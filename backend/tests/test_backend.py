"""Offline tests: no API keys or network needed. The LLM and tools are faked."""
import datetime as dt
import json
import os
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import agent  # noqa: E402
import main  # noqa: E402
import tools  # noqa: E402

TEAMS = [
    {"id": 14, "abbreviation": "LAL", "city": "Los Angeles", "name": "Lakers", "full_name": "Los Angeles Lakers", "conference": "West", "division": "Pacific"},
    {"id": 13, "abbreviation": "LAC", "city": "LA", "name": "Clippers", "full_name": "LA Clippers", "conference": "West", "division": "Pacific"},
    {"id": 3, "abbreviation": "BKN", "city": "Brooklyn", "name": "Nets", "full_name": "Brooklyn Nets", "conference": "East", "division": "Atlantic"},
    {"id": 4, "abbreviation": "CHA", "city": "Charlotte", "name": "Hornets", "full_name": "Charlotte Hornets", "conference": "East", "division": "Southeast"},
    {"id": 25, "abbreviation": "POR", "city": "Portland", "name": "Trail Blazers", "full_name": "Portland Trail Blazers", "conference": "West", "division": "Northwest"},
    {"id": 23, "abbreviation": "PHI", "city": "Philadelphia", "name": "76ers", "full_name": "Philadelphia 76ers", "conference": "East", "division": "Atlantic"},
]


# ---------------------------------------------------------------- helpers

@pytest.mark.parametrize(
    "query,expected",
    [
        ("Lakers", "Los Angeles Lakers"),
        ("lal", "Los Angeles Lakers"),
        ("LA Clippers", "LA Clippers"),
        ("Hornets", "Charlotte Hornets"),
        ("Charlotte Hornets", "Charlotte Hornets"),
        ("Nets", "Brooklyn Nets"),
        ("Blazers", "Portland Trail Blazers"),
        ("Trail Blazers", "Portland Trail Blazers"),
        ("Sixers", "Philadelphia 76ers"),
    ],
)
def test_match_team(query, expected):
    team, amb = tools.match_team(query, TEAMS)
    assert amb == []
    assert team["full_name"] == expected


def test_match_team_ambiguous_city():
    team, amb = tools.match_team("Los Angeles", TEAMS)
    assert team is None
    assert set(amb) == {"Los Angeles Lakers", "LA Clippers"}


def test_match_team_unknown():
    assert tools.match_team("Sonics", TEAMS) == (None, [])


def test_normalize_name():
    assert tools.normalize_name("Nikola Jokić") == "nikola jokic"
    assert tools.normalize_name("Jaren Jackson Jr.") == "jaren jackson"
    assert tools.normalize_name("Shai Gilgeous-Alexander") == "shai gilgeous alexander"


def test_current_season():
    assert tools.current_season(dt.date(2026, 11, 25)) == 2026
    assert tools.current_season(dt.date(2027, 3, 1)) == 2026
    assert tools.current_season(dt.date(2026, 9, 30)) == 2025
    assert tools.season_label(2026) == "2026-27"


def test_parse_minutes():
    assert tools.parse_minutes("34:30") == 34.5
    assert tools.parse_minutes("12") == 12
    assert tools.parse_minutes("") == 0
    assert tools.parse_minutes(None) == 0
    assert tools.parse_minutes("garbage") == 0


def test_average_games_drops_dnps_and_playoffs():
    games = [
        {"min": "30", "pts": 20, "reb": 10, "fgm": 8, "fga": 16, "game": {"postseason": False}},
        {"min": "40", "pts": 30, "reb": 6, "fgm": 12, "fga": 20, "game": {"postseason": False}},
        {"min": "0", "pts": 0, "reb": 0, "fgm": 0, "fga": 0, "game": {"postseason": False}},  # DNP
        {"min": "44", "pts": 50, "reb": 0, "fgm": 20, "fga": 25, "game": {"postseason": True}},  # playoffs
    ]
    avg = tools.average_games(games)
    assert avg["games_played"] == 2
    assert avg["pts"] == 25
    assert avg["reb"] == 8
    assert avg["fg_pct"] == round(20 / 36, 3)  # attempt-weighted
    assert avg["min"] == 35


def test_average_games_empty():
    assert tools.average_games([]) is None
    assert tools.average_games([{"min": "0", "pts": 0}]) is None


def test_normalize_report_coerces_bad_values():
    r = agent.normalize_report(
        {
            "headline": "  Big swing ",
            "trade_grade": "b+",
            "win_prob_delta": "250",
            "confidence": "VERY",
            "pros": "only one",
            "key_stat_comparisons": [{"stat": "PPG", "before": 20}, "junk", {"before": "x"}],
            "counterpart": {"team": "Knicks", "grade": "Z", "take": "fine"},
        }
    )
    assert r["headline"] == "Big swing"
    assert r["trade_grade"] == "B+"
    assert r["win_prob_delta"] == 40.0
    assert r["confidence"] == "medium"
    assert r["pros"] == ["only one"]
    assert r["cons"] == []
    assert r["key_stat_comparisons"] == [{"stat": "PPG", "before": "20", "after": "-"}]
    assert r["counterpart"]["grade"] == "C"
    assert "historical_parallel" not in r


def test_normalize_report_handles_garbage():
    r = agent.normalize_report(None)
    assert r["trade_grade"] == "C" and r["win_prob_delta"] == 0.0


def test_request_validation():
    from fastapi.testclient import TestClient

    c = TestClient(main.app)
    assert c.post("/analyze/stream", json={"team": "Lakers", "trade_description": "  "}).status_code == 422
    assert c.post("/analyze/stream", json={"team": "Lakers", "trade_description": "x" * 600}).status_code == 422


# ---------------------------------------------------------------- end to end

def _tool_use(id_, name, inp):
    return SimpleNamespace(type="tool_use", id=id_, name=name, input=inp)


def _resp(content, stop="tool_use"):
    return SimpleNamespace(content=content, stop_reason=stop)


class FakeMessages:
    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        step = self.script.pop(0) if self.script else self.script_default(kwargs)
        if isinstance(step, Exception):
            raise step
        return step

    def script_default(self, kwargs):
        if kwargs.get("tool_choice"):
            return _resp([_tool_use("f", "finalize_report", REPORT)])
        # keep asking for tools forever: used to prove the loop cap works
        return _resp([_tool_use(f"t{len(self.calls)}", "search_trade_news", {"query": "x"})])


REPORT = {
    "headline": "Knicks land a title-level hub",
    "trade_grade": "A-",
    "win_prob_delta": 9.5,
    "confidence": "high",
    "roster_fit_summary": "Fits.",
    "pros": ["Elite passing"],
    "cons": ["Thin depth"],
    "verdict": "Do it.",
    "counterpart": {"team": "Nuggets", "grade": "D", "take": "Rebuild time."},
}


@pytest.fixture
def fake_env(monkeypatch):
    async def roster(team_name):
        return {"team": "New York Knicks", "roster": [{"name": "Jalen Brunson"}]}

    async def stats(player_name, season=None):
        return {"player": player_name, "team": "Denver Nuggets", "season": 2026, "stats": {"pts": 27.1, "reb": 12.3, "ast": 9.8}}

    async def news(query):
        return {"sources": [{"title": "A", "url": "https://a.test"}, {"title": "A dup", "url": "https://a.test"}]}

    monkeypatch.setitem(agent.TOOL_FUNCTIONS, "get_team_roster", roster)
    monkeypatch.setitem(agent.TOOL_FUNCTIONS, "get_player_stats", stats)
    monkeypatch.setitem(agent.TOOL_FUNCTIONS, "search_trade_news", news)
    main._hits.clear()

    def install(script):
        fake = SimpleNamespace(messages=FakeMessages(script))
        monkeypatch.setattr(agent, "_client", fake)
        return fake

    yield install


def _stream(body=None):
    from fastapi.testclient import TestClient
    from sse_starlette.sse import AppStatus

    AppStatus.should_exit_event = None  # sse-starlette binds this to the first event loop
    c = TestClient(main.app)
    events = []
    with c.stream("POST", "/analyze/stream", json=body or {"team": "Knicks", "trade_description": "Nikola Jokic is traded to the Knicks"}) as r:
        assert r.status_code == 200
        ev = None
        for line in r.iter_lines():
            if line.startswith("event:"):
                ev = line[6:].strip()
            elif line.startswith("data:"):
                events.append((ev, json.loads(line[5:].strip())))
    return events


def test_stream_happy_path(fake_env):
    fake = fake_env(
        [
            _resp([
                _tool_use("a", "get_team_roster", {"team_name": "Knicks"}),
                _tool_use("b", "get_player_stats", {"player_name": "Nikola Jokic"}),
                _tool_use("c", "search_trade_news", {"query": "Jokic Knicks"}),
            ]),
            _resp([SimpleNamespace(type="text", text="enough")], stop="end_turn"),
            _resp([_tool_use("f", "finalize_report", REPORT)]),
        ]
    )
    events = _stream()
    names = [e for e, _ in events]

    tool_events = [d for e, d in events if e == "tool"]
    assert [t["status"] for t in tool_events].count("running") == 3
    assert [t["status"] for t in tool_events].count("ok") == 3
    assert names.index("player") < names.index("report")  # players stream before the report
    assert names[-1] == "done"
    assert "error" not in names

    report = next(d for e, d in events if e == "report")
    assert report["trade_grade"] == "A-" and report["counterpart"]["team"] == "Nuggets"
    sources = next(d for e, d in events if e == "sources")
    assert len(sources) == 1  # deduped by url

    # the user's move is sent inside <move> tags with today's season context
    first_prompt = fake.messages.calls[0]["messages"][0]["content"]
    assert "<move>Nikola Jokic is traded to the Knicks</move>" in first_prompt
    assert "current NBA season" in first_prompt

    # finalize keeps strict role alternation
    final_msgs = fake.messages.calls[-1]["messages"]
    roles = [m["role"] for m in final_msgs]
    assert all(a != b for a, b in zip(roles, roles[1:]))


def test_stream_loop_is_capped(fake_env):
    fake = fake_env([])  # model asks for tools forever
    events = _stream()
    gather_calls = [c for c in fake.messages.calls if not c.get("tool_choice")]
    assert len(gather_calls) == agent.MAX_GATHER_TURNS
    assert any(e == "report" for e, _ in events)
    # finalize after a tool turn folds the instruction into the tool_result message
    last_user = fake.messages.calls[-1]["messages"][-1]
    assert last_user["role"] == "user" and last_user["content"][-1]["type"] == "text"


def test_stream_reports_errors_instead_of_hanging(fake_env):
    import anthropic
    import httpx

    req = httpx.Request("POST", "https://api.anthropic.com")
    err = anthropic.AuthenticationError("bad key", response=httpx.Response(401, request=req), body=None)
    fake_env([err])
    events = _stream()
    names = [e for e, _ in events]
    assert names[-2:] == ["error", "done"]
    assert "API key" in events[-2][1]["message"]


def test_tool_failures_dont_kill_run(fake_env, monkeypatch):
    async def boom(team_name):
        raise RuntimeError("kaboom")

    monkeypatch.setitem(agent.TOOL_FUNCTIONS, "get_team_roster", boom)
    fake = fake_env(
        [
            _resp([_tool_use("a", "get_team_roster", {"team_name": "Knicks"}), _tool_use("b", "get_team_roster", {"wrong_arg": 1})]),
            _resp([SimpleNamespace(type="text", text="ok")], stop="end_turn"),
            _resp([_tool_use("f", "finalize_report", REPORT)]),
        ]
    )
    events = _stream()
    statuses = [d["status"] for e, d in events if e == "tool" and d["status"] != "running"]
    assert statuses == ["error", "error"]
    assert any(e == "report" for e, _ in events)
    tool_results = fake.messages.calls[1]["messages"][-1]["content"]
    assert all(tr.get("is_error") for tr in tool_results)


def test_rate_limit(fake_env, monkeypatch):
    from fastapi.testclient import TestClient

    monkeypatch.setattr(main, "RATE_LIMIT_PER_HOUR", 1)
    fake_env([])
    _stream()
    r = TestClient(main.app).post("/analyze/stream", json={"team": "Knicks", "trade_description": "Jokic to the Knicks"})
    assert r.status_code == 429
