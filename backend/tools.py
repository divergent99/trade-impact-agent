"""
Tool implementations for the Trade Impact Agent.
All async so multiple tool calls in a single Claude turn can run concurrently
instead of blocking one after another.
"""
import asyncio
import os
import httpx
from tavily import AsyncTavilyClient

BDL_BASE = "https://api.balldontlie.io/v1"
NBA_V1_BASE = "https://api.balldontlie.io/nba/v1"  # newer endpoint family — injuries lives here, not the legacy base
BDL_KEY = os.environ.get("BALLDONTLIE_API_KEY", "")

_tavily = AsyncTavilyClient(api_key=os.environ.get("TAVILY_API_KEY", ""))


def _bdl_headers():
    return {"Authorization": BDL_KEY}


async def _bdl_get(client: httpx.AsyncClient, path: str, params: dict | None = None, base: str = BDL_BASE) -> httpx.Response:
    """GET against balldontlie with a single automatic retry on 429.

    The free tier's rate limit is easy to hit when several tool calls fire
    close together (which we do on purpose, for speed) — a demo re-run a
    couple times in a row can trip it. One short backoff-and-retry covers
    that without adding much latency to the common case.
    """
    resp = await client.get(f"{base}{path}", headers=_bdl_headers(), params=params)
    if resp.status_code == 429:
        retry_after = resp.headers.get("Retry-After")
        try:
            delay = min(float(retry_after), 5) if retry_after else 1.5
        except ValueError:
            delay = 1.5
        await asyncio.sleep(delay)
        resp = await client.get(f"{base}{path}", headers=_bdl_headers(), params=params)
    return resp


async def get_team_roster(team_name: str) -> dict:
    """Look up a team by name/city and return its current roster."""
    async with httpx.AsyncClient(timeout=15) as client:
        teams_resp = await _bdl_get(client, "/teams")
        teams_resp.raise_for_status()
        teams = teams_resp.json().get("data", [])

        match = next(
            (
                t for t in teams
                if team_name.lower() in t["full_name"].lower()
                or team_name.lower() in t["name"].lower()
                or team_name.lower() == t["abbreviation"].lower()
            ),
            None,
        )
        if not match:
            return {"error": f"No team found matching '{team_name}'"}

        players_resp = await _bdl_get(client, "/players", params={"team_ids[]": match["id"], "per_page": 100})
        players_resp.raise_for_status()
        players = players_resp.json().get("data", [])

        return {
            "team": match["full_name"],
            "abbreviation": match["abbreviation"],
            "conference": match.get("conference"),
            "division": match.get("division"),
            "roster": [
                {
                    "name": f"{p['first_name']} {p['last_name']}",
                    "position": p.get("position"),
                    "id": p["id"],
                }
                for p in players
            ],
        }


async def _find_player(client: httpx.AsyncClient, name: str) -> dict | None:
    """Search for a player by name.

    balldontlie's search has two quirks that combine into a real bug if not
    handled carefully:
      1. A combined "First Last" query can return empty even though the
         player exists.
      2. Searching on a single name part (e.g. "James") can match a totally
         different player who happens to share that part as their FIRST
         name (e.g. "James Ennis III"), not just the intended surname match.

    So: try progressively narrower search terms, but only ever accept a
    result whose full "first last" name exactly matches the query — never
    just take result[0] from a fuzzy match.
    """
    target = name.strip().lower()
    parts = target.split()

    async def search(term: str) -> list:
        resp = await _bdl_get(client, "/players", params={"search": term, "per_page": 100})
        resp.raise_for_status()
        return resp.json().get("data", [])

    def exact_match(candidates: list):
        for p in candidates:
            full = f"{p['first_name']} {p['last_name']}".strip().lower()
            if full == target:
                return p
        return None

    candidates = await search(name)
    match = exact_match(candidates)
    if match:
        return match

    if len(parts) > 1:
        for term in (parts[-1], parts[0]):
            candidates = await search(term)
            match = exact_match(candidates)
            if match:
                return match

    # last resort: no exact match found anywhere, fall back to the first
    # fuzzy result rather than failing outright — better than nothing, but
    # this is a guess, not a verified match
    for term in [name] + parts:
        candidates = await search(term)
        if candidates:
            return candidates[0]

    return None


AVG_FIELDS = ["pts", "reb", "ast", "stl", "blk", "fg_pct", "fg3_pct", "ft_pct", "oreb", "dreb", "turnover", "pf"]


async def _average_from_game_logs(client: httpx.AsyncClient, player_id: int, season: int) -> dict | None:
    """balldontlie's precomputed season_averages endpoint is GOAT-tier only,
    but individual game stats (/stats) are included on ALL-STAR. Pull the
    season's games and average the numeric fields ourselves — same end
    result, cheaper tier. Note: this doesn't filter out playoff games (the
    documented filter param name is unreliable), so a player deep in a
    playoff run will have those games blended into the average.
    """
    resp = await _bdl_get(client, "/stats", params={"player_ids[]": player_id, "seasons[]": season, "per_page": 100})
    if resp.status_code != 200:
        return None
    games = resp.json().get("data", [])
    if not games:
        return None

    sums = {f: 0.0 for f in AVG_FIELDS}
    counts = {f: 0 for f in AVG_FIELDS}
    for g in games:
        for f in AVG_FIELDS:
            v = g.get(f)
            if isinstance(v, (int, float)):
                sums[f] += v
                counts[f] += 1

    averaged = {f: round(sums[f] / counts[f], 3) for f in AVG_FIELDS if counts[f] > 0}
    averaged["games_played"] = len(games)
    return averaged


async def _get_injury_status(client: httpx.AsyncClient, player_id: int) -> dict | None:
    """Check current injury report for a player (ALL-STAR tier). Lives at
    the newer /nba/v1/ base, not the legacy one everything else uses.
    """
    resp = await _bdl_get(client, "/player_injuries", params={"player_ids[]": player_id}, base=NBA_V1_BASE)
    if resp.status_code != 200:
        return None
    entries = resp.json().get("data", [])
    if not entries:
        return None
    entry = entries[0]
    return {
        "status": entry.get("status"),
        "description": entry.get("description"),
        "return_date": entry.get("return_date"),
    }


async def get_player_stats(player_name: str, season: int = 2024) -> dict:
    """Search for a player and return season stats plus current injury status.

    Tries three tiers of stat data, each requiring a lower balldontlie plan
    than the last, so this keeps working regardless of which tier is active:
      1. season_averages (GOAT tier) — balldontlie's own precomputed average
      2. /stats game logs, averaged ourselves (ALL-STAR tier)
      3. bio data only — position, height, weight, draft info (free tier)
    Injury status (ALL-STAR tier) is checked in parallel and attached
    regardless of which stats tier was used.
    """
    async with httpx.AsyncClient(timeout=15) as client:
        player = await _find_player(client, player_name)
        if not player:
            return {"error": f"No player found matching '{player_name}'"}

        bio = {
            "player": f"{player['first_name']} {player['last_name']}",
            "team": player.get("team", {}).get("full_name"),
            "position": player.get("position"),
            "height": player.get("height"),
            "weight": player.get("weight"),
            "college": player.get("college"),
            "draft_year": player.get("draft_year"),
            "draft_round": player.get("draft_round"),
            "draft_number": player.get("draft_number"),
        }

        injury = await _get_injury_status(client, player["id"])
        if injury:
            bio["injury"] = injury

        stats_resp = await _bdl_get(
            client, "/season_averages", params={"season": season, "player_id": player["id"]}
        )

        if stats_resp.status_code in (400, 401):
            # 401 = tier doesn't include this endpoint at all.
            # 400 = tier is fine but this legacy endpoint's param shape is
            # different from what we sent (or from newer balldontlie
            # endpoints) — either way, fall back to averaging /stats
            # ourselves (ALL-STAR tier) rather than erroring out.
            averaged = await _average_from_game_logs(client, player["id"], season)
            if averaged:
                return {
                    **bio,
                    "season": season,
                    "stats": averaged,
                    "stats_note": "Averaged from individual games",
                }
            return {
                **bio,
                "season": season,
                "stats": None,
                "stats_note": "Stats require a paid balldontlie plan",
            }

        stats_resp.raise_for_status()
        stats = stats_resp.json().get("data", [])

        return {
            **bio,
            "season": season,
            "stats": stats[0] if stats else None,
        }


async def search_trade_news(query: str) -> dict:
    """Search for recent trade rumor / news context via Tavily."""
    result = await _tavily.search(
        query=query,
        search_depth="basic",
        max_results=5,
        include_answer=True,
        topic="news",
    )
    return {
        "answer": result.get("answer"),
        "sources": [
            {
                "title": r["title"],
                "url": r["url"],
                "content": r["content"][:500],
                "published": r.get("published_date"),
            }
            for r in result.get("results", [])
        ],
    }


# Anthropic tool schemas. cache_control on the last one caches the entire
# system prompt + tools prefix, since Anthropic caches everything up to and
# including the marked block. This prefix is identical on every gather turn,
# so turns 2+ skip re-processing it.
TOOL_SCHEMAS = [
    {
        "name": "get_team_roster",
        "description": "Get an NBA team's current roster by team name, city, or abbreviation (e.g. 'Lakers', 'Los Angeles', 'LAL').",
        "input_schema": {
            "type": "object",
            "properties": {
                "team_name": {"type": "string", "description": "Team name, city, or abbreviation"}
            },
            "required": ["team_name"],
        },
    },
    {
        "name": "get_player_stats",
        "description": "Get an NBA player's season average stats (points, rebounds, assists, etc.) and current injury status, if any, by name.",
        "input_schema": {
            "type": "object",
            "properties": {
                "player_name": {"type": "string", "description": "Player full or partial name"},
                "season": {"type": "integer", "description": "Season year, e.g. 2024 for 2024-25 season", "default": 2024},
            },
            "required": ["player_name"],
        },
    },
    {
        "name": "search_trade_news",
        "description": "Search recent news for trade rumors, context, or reactions related to a query.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query, e.g. 'Lakers Lebron James trade rumors 2026'"}
            },
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