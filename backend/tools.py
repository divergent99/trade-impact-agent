"""
Tool implementations for the Trade Impact Agent.

Everything is async so multiple tool calls from a single Claude turn run
concurrently. Every public tool returns a dict and never raises: failures come
back as {"error": "..."} so the agent can keep going with partial data instead
of the whole run dying on one flaky API call.
"""
import asyncio
import datetime as dt
import logging
import os
import re
import time
import unicodedata
from collections import deque

import httpx

BDL_BASE = "https://api.balldontlie.io/v1"
NBA_V1_BASE = "https://api.balldontlie.io/nba/v1"  # newer endpoint family (injuries live here on some plans)

HTTP_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


def bdl_key() -> str:
    return os.environ.get("BALLDONTLIE_API_KEY", "").strip()


def tavily_key() -> str:
    return os.environ.get("TAVILY_API_KEY", "").strip()


def current_season(today: dt.date | None = None) -> int:
    """balldontlie labels a season by its start year. The NBA regular season
    tips off in October, so Oct-Dec belongs to this year's season and
    Jan-Sep to last year's."""
    today = today or dt.date.today()
    return today.year if today.month >= 10 else today.year - 1


def season_label(season: int) -> str:
    return f"{season}-{str(season + 1)[-2:]}"


# ---------------------------------------------------------------------------
# HTTP plumbing
# ---------------------------------------------------------------------------

_http: httpx.AsyncClient | None = None


def http_client() -> httpx.AsyncClient:
    """One shared client so connections get pooled across tool calls."""
    global _http
    if _http is None or _http.is_closed:
        _http = httpx.AsyncClient(timeout=HTTP_TIMEOUT)
    return _http


async def close_http_client():
    global _http
    if _http is not None and not _http.is_closed:
        await _http.aclose()
    _http = None


class ToolError(Exception):
    """Raised inside tool internals, converted to {"error": ...} at the edge."""


log = logging.getLogger("trade-desk.bdl")

# balldontlie plans are rate limited per minute (free 5, ALL-STAR 60, GOAT 600).
# Pace requests client-side so a burst of parallel tool calls queues briefly
# instead of tripping 429s and cascading into timeouts.
BDL_REQUESTS_PER_MIN = int(os.environ.get("BDL_REQUESTS_PER_MIN", "55"))
CACHE_TTL_SECONDS = float(os.environ.get("BDL_CACHE_TTL_SECONDS", "600"))


class RateLimited(Exception):
    pass


class _MinuteWindow:
    """Sliding 60s window limiter shared by every balldontlie call in the process."""

    def __init__(self, per_minute: int):
        self.per_minute = max(1, per_minute)
        self.stamps: deque = deque()
        self.lock = asyncio.Lock()

    async def acquire(self):
        while True:
            async with self.lock:
                now = time.monotonic()
                while self.stamps and now - self.stamps[0] >= 60:
                    self.stamps.popleft()
                if len(self.stamps) < self.per_minute:
                    self.stamps.append(now)
                    return
                wait = 60 - (now - self.stamps[0]) + 0.05
            await asyncio.sleep(min(wait, 2.0))


_window: _MinuteWindow | None = None


def _limiter() -> _MinuteWindow:
    global _window
    if _window is None:
        _window = _MinuteWindow(BDL_REQUESTS_PER_MIN)
    return _window


# endpoints this API key's plan can't use (401/403/404), learned at runtime so
# we stop spending rate limit on calls that will never work
_unsupported: set[str] = set()


def _mark_unsupported(base: str, path: str, resp: httpx.Response):
    if resp.status_code in (401, 403, 404):
        if f"{base}{path}" not in _unsupported:
            log.info("balldontlie %s%s -> %s, skipping it from now on", base.split("/")[-1], path, resp.status_code)
        _unsupported.add(f"{base}{path}")


def _supported(base: str, path: str) -> bool:
    return f"{base}{path}" not in _unsupported


class _TTLCache:
    def __init__(self, ttl: float):
        self.ttl = ttl
        self.data: dict = {}

    def get(self, key):
        hit = self.data.get(key)
        if hit and time.monotonic() - hit[0] < self.ttl:
            return hit[1]
        return None

    def set(self, key, value):
        if len(self.data) > 2000:
            self.data.clear()
        self.data[key] = (time.monotonic(), value)


_player_cache = _TTLCache(CACHE_TTL_SECONDS * 6)  # name -> player record barely changes
_stats_cache = _TTLCache(CACHE_TTL_SECONDS)
_injury_cache = _TTLCache(CACHE_TTL_SECONDS / 2)
_roster_cache = _TTLCache(CACHE_TTL_SECONDS)


async def _bdl_get(path: str, params: dict | None = None, base: str = BDL_BASE) -> httpx.Response:
    """Paced GET against balldontlie. One retry on network blips or a short
    429; a longer 429 raises RateLimited immediately so callers stop instead of
    piling fallback calls onto an exhausted quota."""
    if not bdl_key():
        raise ToolError("BALLDONTLIE_API_KEY is not set on the server")

    client = http_client()
    url = f"{base}{path}"
    headers = {"Authorization": bdl_key()}
    last_exc: Exception | None = None

    for attempt in range(2):
        await _limiter().acquire()
        started = time.perf_counter()
        try:
            resp = await client.get(url, headers=headers, params=params)
        except (httpx.TimeoutException, httpx.TransportError) as e:
            last_exc = e
            log.warning("balldontlie %s failed: %s", path, type(e).__name__)
            await asyncio.sleep(0.5)
            continue
        log.info("balldontlie %s %s %dms", path, resp.status_code, (time.perf_counter() - started) * 1000)

        if resp.status_code != 429:
            return resp
        retry_after = resp.headers.get("Retry-After")
        try:
            delay = float(retry_after) if retry_after else 2.0
        except ValueError:
            delay = 2.0
        if attempt == 1 or delay > 3:
            raise RateLimited()
        await asyncio.sleep(delay)

    raise ToolError(f"balldontlie unreachable ({type(last_exc).__name__})")


RATE_LIMIT_MSG = "balldontlie rate limit reached for this API plan; try again in a minute"


def _explain_status(resp: httpx.Response) -> str:
    code = resp.status_code
    if code == 401:
        return "balldontlie rejected the request (401): key invalid or plan lacks this endpoint"
    if code == 429:
        return "balldontlie rate limit hit (429), try again in a minute"
    return f"balldontlie returned HTTP {code}"


# ---------------------------------------------------------------------------
# Name normalization / matching
# ---------------------------------------------------------------------------

_SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}


def normalize_name(name: str) -> str:
    """'Nikola Jokić' -> 'nikola jokic', 'Jaren Jackson Jr.' -> 'jaren jackson'."""
    s = unicodedata.normalize("NFKD", name or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    tokens = [t for t in s.split() if t not in _SUFFIXES]
    return " ".join(tokens)


def _full_name(p: dict) -> str:
    return f"{p.get('first_name', '')} {p.get('last_name', '')}".strip()


TEAM_ALIASES = {
    "sixers": "76ers",
    "philly": "76ers",
    "blazers": "trail blazers",
    "portland": "trail blazers",
    "cavs": "cavaliers",
    "mavs": "mavericks",
    "wolves": "timberwolves",
    "t-wolves": "timberwolves",
    "dubs": "warriors",
    "nola": "pelicans",
    "okc": "thunder",
    "griz": "grizzlies",
    "clips": "clippers",
    "knickerbockers": "knicks",
}


def match_team(query: str, teams: list[dict]) -> tuple[dict | None, list[str]]:
    """Return (team, ambiguous_candidates). Tries strict matches first so
    'Los Angeles' doesn't silently resolve to whichever LA team comes first."""
    q = (query or "").strip().lower()
    q = TEAM_ALIASES.get(q, q)
    if not q:
        return None, []

    def norm(s):
        return (s or "").strip().lower()

    for key in ("abbreviation", "name", "full_name"):
        hits = [t for t in teams if norm(t.get(key)) == q]
        if len(hits) == 1:
            return hits[0], []

    # cities: the Clippers are listed as "LA", the Lakers as "Los Angeles",
    # so a bare "Los Angeles" must come back ambiguous rather than Lakers
    def city(s):
        c = norm(s)
        return "los angeles" if c in ("la", "l a", "l.a.") else c

    hits = [t for t in teams if city(t.get("city")) == city(q)]
    if len(hits) == 1:
        return hits[0], []
    if len(hits) > 1:
        return None, [t["full_name"] for t in hits]

    # token-based containment, so "nets" never matches "charlotte hornets"
    q_tokens = set(re.findall(r"[a-z0-9]+", q))
    hits = [
        t
        for t in teams
        if set(re.findall(r"[a-z0-9]+", norm(t.get("name")))) <= q_tokens
        or (len(q) >= 3 and q in norm(t.get("full_name")))
    ]
    if len(hits) == 1:
        return hits[0], []
    if len(hits) > 1:
        return None, [t["full_name"] for t in hits]
    return None, []


# ---------------------------------------------------------------------------
# Teams + rosters
# ---------------------------------------------------------------------------

_teams_cache: list[dict] | None = None
_teams_lock = asyncio.Lock()


async def _get_teams() -> list[dict]:
    """The 30 franchises basically never change, so fetch once per process."""
    global _teams_cache
    async with _teams_lock:
        if _teams_cache is not None:
            return _teams_cache
        resp = await _bdl_get("/teams", params={"per_page": 100})
        if resp.status_code != 200:
            raise ToolError(_explain_status(resp))
        teams = resp.json().get("data", [])
        # newer API versions include defunct franchises with blank conference/division
        current = [t for t in teams if (t.get("conference") or "").strip() and (t.get("division") or "").strip()]
        _teams_cache = current or teams
        return _teams_cache


async def get_team_roster(team_name: str) -> dict:
    """Look up a team by name/city/abbreviation and return its current roster."""
    try:
        teams = await _get_teams()
        team, ambiguous = match_team(team_name, teams)
        if ambiguous:
            return {"error": f"'{team_name}' is ambiguous, pick one of: {', '.join(ambiguous)}"}
        if not team:
            return {"error": f"No NBA team found matching '{team_name}'"}

        cached = _roster_cache.get(team["id"])
        if cached:
            return cached

        params = {"team_ids[]": team["id"], "per_page": 100}
        # /players/active excludes retired players; it's a paid endpoint, so
        # fall back to /players (which includes historical players) if needed
        roster_note = None
        resp = None
        if _supported(BDL_BASE, "/players/active"):
            resp = await _bdl_get("/players/active", params=params)
            _mark_unsupported(BDL_BASE, "/players/active", resp)
        if resp is None or resp.status_code != 200:
            resp = await _bdl_get("/players", params=params)
            roster_note = "Active-roster endpoint unavailable on this plan; list may include former players"
        if resp.status_code != 200:
            return {"error": _explain_status(resp)}

        players = resp.json().get("data", [])
        result = {
            "team": team["full_name"],
            "abbreviation": team.get("abbreviation"),
            "conference": team.get("conference"),
            "division": team.get("division"),
            "roster": [
                {"name": _full_name(p), "position": p.get("position") or None, "jersey": p.get("jersey_number")}
                for p in players
            ],
        }
        if roster_note:
            result["note"] = roster_note
        _roster_cache.set(team["id"], result)
        return result
    except RateLimited:
        return {"error": RATE_LIMIT_MSG}
    except ToolError as e:
        return {"error": str(e)}
    except Exception as e:  # never let a tool take down the run
        return {"error": f"get_team_roster failed: {type(e).__name__}"}


# ---------------------------------------------------------------------------
# Players
# ---------------------------------------------------------------------------

async def _search_players(term: str, active: bool) -> list[dict]:
    path = "/players/active" if active else "/players"
    if not _supported(BDL_BASE, path):
        return []
    resp = await _bdl_get(path, params={"search": term, "per_page": 100})
    _mark_unsupported(BDL_BASE, path, resp)
    if resp.status_code != 200:
        return []
    return resp.json().get("data", [])


async def find_player(name: str) -> tuple[dict | None, str]:
    """Search for a player by name. Returns (player, match_quality).

    balldontlie's search has two quirks:
      1. A combined "First Last" query can come back empty even though the
         player exists.
      2. A single-token search ("James") matches anyone with that token as a
         first OR last name.
    So we try progressively looser search terms but only accept a result whose
    normalized full name equals the query. Active players are preferred so a
    retired namesake never wins. Results are cached, so re-runs and repeat
    lookups cost no API calls. Usually this is a single request.
    """
    target = normalize_name(name)
    if not target:
        return None, "none"
    cached = _player_cache.get(target)
    if cached:
        return cached

    parts = target.split()
    # last name alone is the most reliable single search for hyphenated or
    # accented names ("Karl-Anthony Towns", "Jokić")
    terms = [name.strip()] + ([parts[-1]] if len(parts) > 1 else [])

    seen: dict[int, dict] = {}
    for active in (True, False):
        if not active and seen:
            break  # active search found candidates; don't spend calls on retired players
        for term in terms:
            for p in await _search_players(term, active):
                seen.setdefault(p["id"], p)
                if normalize_name(_full_name(p)) == target:
                    _player_cache.set(target, (p, "exact"))
                    return p, "exact"

    # fuzzy: every query token appears somewhere in the candidate's name
    for p in seen.values():
        cand = normalize_name(_full_name(p)).split()
        if all(any(c.startswith(t) for c in cand) for t in parts):
            _player_cache.set(target, (p, "fuzzy"))
            return p, "fuzzy"
    return None, "none"


AVG_FIELDS = ["pts", "reb", "ast", "stl", "blk", "fg_pct", "fg3_pct", "ft_pct", "oreb", "dreb", "turnover", "pf"]


def parse_minutes(raw) -> float:
    """balldontlie sends minutes as '34', '34:12', '' or None."""
    if raw is None:
        return 0.0
    if isinstance(raw, (int, float)):
        return float(raw)
    s = str(raw).strip()
    if not s:
        return 0.0
    try:
        if ":" in s:
            m, sec = s.split(":", 1)
            return int(m) + int(sec) / 60
        return float(s)
    except ValueError:
        return 0.0


def average_games(games: list[dict]) -> dict | None:
    """Average box-score fields over regular-season games the player actually
    played in. DNPs (0 minutes) would drag every number down, and playoff
    games would skew a season average, so both are dropped when possible."""
    played = [g for g in games if parse_minutes(g.get("min")) > 0]
    regular = [g for g in played if not (g.get("game") or {}).get("postseason")]
    sample = regular or played
    if not sample:
        return None

    sums = {f: 0.0 for f in AVG_FIELDS}
    counts = {f: 0 for f in AVG_FIELDS}
    for g in sample:
        for f in AVG_FIELDS:
            v = g.get(f)
            if isinstance(v, (int, float)):
                sums[f] += v
                counts[f] += 1

    # shooting % should be weighted by attempts, not averaged per game
    def weighted(made, att):
        m = sum(g.get(made) or 0 for g in sample)
        a = sum(g.get(att) or 0 for g in sample)
        return round(m / a, 3) if a else None

    out = {f: round(sums[f] / counts[f], 3) for f in AVG_FIELDS if counts[f] > 0}
    for pct, made, att in (("fg_pct", "fgm", "fga"), ("fg3_pct", "fg3m", "fg3a"), ("ft_pct", "ftm", "fta")):
        w = weighted(made, att)
        if w is not None:
            out[pct] = w
    out["min"] = round(sum(parse_minutes(g.get("min")) for g in sample) / len(sample), 1)
    out["games_played"] = len(sample)
    return out


async def _season_from_game_logs(player_id: int, season: int) -> tuple[dict | None, bool]:
    """Returns (averages, api_ok). api_ok=False means the endpoint failed,
    as opposed to working fine and returning zero games."""
    games: list[dict] = []
    cursor = None
    for _ in range(2):  # 100 per page; a second page only matters late in the season
        params = {"player_ids[]": player_id, "seasons[]": season, "per_page": 100}
        if cursor:
            params["cursor"] = cursor
        resp = await _bdl_get("/stats", params=params)
        if resp.status_code != 200:
            _mark_unsupported(BDL_BASE, "/stats", resp)
            return None, False
        body = resp.json()
        games.extend(body.get("data", []))
        cursor = (body.get("meta") or {}).get("next_cursor")
        if not cursor:
            break
    return average_games(games), True


async def _season_stats(player_id: int, season: int) -> tuple[dict | None, str | None, bool]:
    """Precomputed season_averages -> averaged game logs -> nothing.
    Returns (stats, note, api_ok). Cached per player+season."""
    key = (player_id, season)
    cached = _stats_cache.get(key)
    if cached:
        return cached

    result = (None, None, False)
    if _supported(BDL_BASE, "/season_averages"):
        resp = await _bdl_get("/season_averages", params={"season": season, "player_id": player_id})
        if resp.status_code == 200:
            data = resp.json().get("data") or []
            if data:
                result = (data[0], None, True)
        elif resp.status_code == 400:
            # legacy param shape rejected by this API version: same as unsupported
            _unsupported.add(f"{BDL_BASE}/season_averages")
        else:
            _mark_unsupported(BDL_BASE, "/season_averages", resp)

    if result[0] is None and _supported(BDL_BASE, "/stats"):
        averaged, ok = await _season_from_game_logs(player_id, season)
        result = (averaged, "Averaged from individual regular-season games" if averaged else None, ok)

    if result[2]:
        _stats_cache.set(key, result)
    return result


async def _get_injury_status(player_id: int) -> dict | None:
    """Current injury report entry, if any. The endpoint has lived under both
    API bases depending on plan/version; whichever fails is skipped afterwards."""
    cached = _injury_cache.get(player_id)
    if cached is not None:
        return cached or None
    for base in (NBA_V1_BASE, BDL_BASE):
        if not _supported(base, "/player_injuries"):
            continue
        resp = await _bdl_get("/player_injuries", params={"player_ids[]": player_id}, base=base)
        if resp.status_code != 200:
            _mark_unsupported(base, "/player_injuries", resp)
            continue
        entries = resp.json().get("data", [])
        e = entries[0] if entries else None
        info = {"status": e.get("status"), "description": e.get("description"), "return_date": e.get("return_date")} if e else {}
        _injury_cache.set(player_id, info)
        return info or None
    return None


STATS_BUDGET_SECONDS = float(os.environ.get("STATS_BUDGET_SECONDS", "18"))


async def get_player_stats(player_name: str, season: int | None = None) -> dict:
    """Find a player and return bio, season stats and current injury status.
    If the requested season has no games yet (early October), falls back to
    the previous season and says so."""
    try:
        season = int(season) if season else current_season()
    except (TypeError, ValueError):
        season = current_season()

    try:
        player, quality = await find_player(player_name)
        if not player:
            return {"error": f"No NBA player found matching '{player_name}'"}

        bio = {
            "player": _full_name(player),
            "player_id": player["id"],
            "match": quality,
            "team": (player.get("team") or {}).get("full_name"),
            "position": player.get("position") or None,
            "jersey": player.get("jersey_number") or None,
            "height": player.get("height"),
            "weight": player.get("weight"),
            "college": player.get("college"),
            "country": player.get("country"),
            "draft_year": player.get("draft_year"),
            "draft_round": player.get("draft_round"),
            "draft_number": player.get("draft_number"),
        }
        if quality == "fuzzy":
            bio["match_note"] = f"No exact match for '{player_name}', closest was {bio['player']}"

        async def stats_and_injury():
            (stats, note, ok), injury = await asyncio.gather(
                _season_stats(player["id"], season),
                _get_injury_status(player["id"]),
                return_exceptions=False,
            )
            used = season
            # only fall back a season when the API worked and simply had no games yet
            if stats is None and ok and season == current_season():
                prev, prev_note, _ = await _season_stats(player["id"], season - 1)
                if prev is not None:
                    stats, used = prev, season - 1
                    note = f"No {season_label(season)} games yet; showing {season_label(season - 1)}" + (
                        f". {prev_note}" if prev_note else ""
                    )
            return stats, note, used, injury

        note = None
        try:
            stats, note, used_season, injury = await asyncio.wait_for(stats_and_injury(), timeout=STATS_BUDGET_SECONDS)
        except asyncio.TimeoutError:
            stats, used_season, injury = None, season, None
            note = "Stats lookup timed out (balldontlie slow or rate-limited); bio only"
        except RateLimited:
            stats, used_season, injury = None, season, None
            note = "balldontlie rate limit reached; bio only. Re-run in a minute for full stats"

        result = {**bio, "season": used_season, "stats": stats}
        if stats is None and not note:
            note = "Season stats unavailable (plan limit or no games played); bio only"
        if note:
            result["stats_note"] = note
        if injury and injury.get("status"):
            result["injury"] = injury
        return result
    except RateLimited:
        return {"error": RATE_LIMIT_MSG}
    except ToolError as e:
        return {"error": str(e)}
    except Exception as e:
        log.exception("get_player_stats failed")
        return {"error": f"get_player_stats failed: {type(e).__name__}"}


# ---------------------------------------------------------------------------
# News
# ---------------------------------------------------------------------------

_tavily = None


def _tavily_client():
    global _tavily
    if _tavily is None:
        from tavily import AsyncTavilyClient

        _tavily = AsyncTavilyClient(api_key=tavily_key())
    return _tavily


async def search_trade_news(query: str) -> dict:
    """Search recent news for trade context via Tavily."""
    if not tavily_key():
        return {"error": "TAVILY_API_KEY is not set on the server, news search unavailable"}
    try:
        result = await _tavily_client().search(
            query=query,
            search_depth="basic",
            max_results=6,
            include_answer=True,
            topic="news",
            days=60,
        )
    except Exception as e:
        return {"error": f"News search failed ({type(e).__name__})"}

    sources = []
    seen = set()
    for r in result.get("results", []):
        url = r.get("url")
        if not url or url in seen:
            continue
        seen.add(url)
        sources.append(
            {
                "title": r.get("title") or url,
                "url": url,
                "content": (r.get("content") or "")[:500],
                "published": r.get("published_date"),
            }
        )
    return {"answer": result.get("answer"), "sources": sources}


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

# cache_control on the last tool caches the system prompt + tool prefix,
# which is identical on every gather turn.
TOOL_SCHEMAS = [
    {
        "name": "get_team_roster",
        "description": "Get an NBA team's current roster by team name, city, or abbreviation (e.g. 'Lakers', 'LAL'). Prefer the team nickname; a bare city like 'Los Angeles' is ambiguous.",
        "input_schema": {
            "type": "object",
            "properties": {"team_name": {"type": "string", "description": "Team nickname, full name, or abbreviation"}},
            "required": ["team_name"],
        },
    },
    {
        "name": "get_player_stats",
        "description": "Get an NBA player's season averages (pts, reb, ast, shooting splits, minutes, games) plus current injury status, by full name. Defaults to the current season.",
        "input_schema": {
            "type": "object",
            "properties": {
                "player_name": {"type": "string", "description": "Player full name, e.g. 'Nikola Jokic'"},
                "season": {"type": "integer", "description": "Season start year, e.g. 2025 for 2025-26. Omit for the current season."},
            },
            "required": ["player_name"],
        },
    },
    {
        "name": "search_trade_news",
        "description": "Search the last ~60 days of news for trade rumors, context, cap/contract details, or reactions.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Search query, e.g. 'Knicks Jokic trade'"}},
            "required": ["query"],
        },
        "cache_control": {"type": "ephemeral"},
    },
]

TOOL_FUNCTIONS = {
    "get_team_roster": get_team_roster,
    "get_player_stats": get_player_stats,
    "search_trade_news": search_trade_news,
}


def summarize_tool_result(name: str, result: dict) -> str:
    """One-line human summary of a tool result for the live feed."""
    if result.get("error"):
        return result["error"]
    if name == "get_team_roster":
        return f"{result.get('team')}: {len(result.get('roster', []))} players"
    if name == "get_player_stats":
        s = result.get("stats")
        bits = [result.get("player") or "?"]
        if s:
            bits.append(f"{s.get('pts', 0):.1f} pts / {s.get('reb', 0):.1f} reb / {s.get('ast', 0):.1f} ast")
        else:
            bits.append("bio only")
        if result.get("injury"):
            bits.append(f"injury: {result['injury'].get('status')}")
        return ", ".join(bits)
    if name == "search_trade_news":
        return f"{len(result.get('sources', []))} articles"
    return "done"
