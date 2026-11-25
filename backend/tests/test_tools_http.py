"""balldontlie tool logic against a mocked HTTP transport (no network)."""
import asyncio
import os
import sys

import httpx
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tools  # noqa: E402

JOKIC = {"id": 246, "first_name": "Nikola", "last_name": "Jokić", "position": "C", "team": {"full_name": "Denver Nuggets"}}
RETIRED_NAMESAKE = {"id": 9, "first_name": "Nikola", "last_name": "Jokic", "position": "F", "team": {"full_name": "Old Team"}}


def reset_state(monkeypatch):
    monkeypatch.setattr(tools, "_teams_cache", None)
    monkeypatch.setattr(tools, "_window", None)
    monkeypatch.setattr(tools, "_unsupported", set())
    for name in ("_player_cache", "_stats_cache", "_injury_cache", "_roster_cache"):
        monkeypatch.setattr(tools, name, tools._TTLCache(600))


def install(monkeypatch, handler, fast_sleep=True):
    monkeypatch.setenv("BALLDONTLIE_API_KEY", "test")
    reset_state(monkeypatch)
    calls = []

    def counting(req):
        calls.append(req.url.path)
        return handler(req)

    monkeypatch.setattr(tools, "_http", httpx.AsyncClient(transport=httpx.MockTransport(counting)))
    if fast_sleep:
        monkeypatch.setattr(tools.asyncio, "sleep", _nosleep)
    return calls


async def _nosleep(*_):
    return None


def run(coro):
    return asyncio.run(coro)


def test_find_player_prefers_active_exact(monkeypatch):
    def handler(req):
        if req.url.path == "/v1/players/active":
            return httpx.Response(200, json={"data": [JOKIC]})
        return httpx.Response(200, json={"data": [RETIRED_NAMESAKE]})

    install(monkeypatch, handler)
    p, q = run(tools.find_player("Nikola Jokic"))
    assert p["id"] == 246 and q == "exact"


def test_stats_fall_back_to_game_logs_and_previous_season(monkeypatch):
    def handler(req):
        path, params = req.url.path, req.url.params
        if path == "/v1/players/active":
            return httpx.Response(200, json={"data": [JOKIC]})
        if path == "/v1/season_averages":
            return httpx.Response(401)
        if path == "/v1/stats":
            season = params.get("seasons[]")
            if season == "2026":
                return httpx.Response(200, json={"data": [], "meta": {}})
            return httpx.Response(200, json={"data": [{"min": "36", "pts": 29, "reb": 13, "ast": 10, "game": {"postseason": False}}], "meta": {}})
        if path.endswith("/player_injuries"):
            return httpx.Response(200, json={"data": [{"status": "Day-To-Day", "description": "ankle"}]})
        return httpx.Response(404)

    install(monkeypatch, handler)
    monkeypatch.setattr(tools, "current_season", lambda today=None: 2026)
    r = run(tools.get_player_stats("Nikola Jokic"))
    assert r["season"] == 2025
    assert r["stats"]["pts"] == 29
    assert "No 2026-27 games yet" in r["stats_note"]
    assert r["injury"]["status"] == "Day-To-Day"


def test_roster_falls_back_and_429_retries(monkeypatch):
    calls = {"teams": 0}

    def handler(req):
        path = req.url.path
        if path == "/v1/teams":
            calls["teams"] += 1
            if calls["teams"] == 1:
                return httpx.Response(429, headers={"Retry-After": "0"})
            return httpx.Response(200, json={"data": [{"id": 20, "abbreviation": "NYK", "city": "New York", "name": "Knicks", "full_name": "New York Knicks", "conference": "East", "division": "Atlantic"}]})
        if path == "/v1/players/active":
            return httpx.Response(401)
        if path == "/v1/players":
            return httpx.Response(200, json={"data": [{"id": 1, "first_name": "Jalen", "last_name": "Brunson", "position": "G"}]})
        return httpx.Response(404)

    install(monkeypatch, handler)
    r = run(tools.get_team_roster("Knicks"))
    assert r["team"] == "New York Knicks"
    assert r["roster"][0]["name"] == "Jalen Brunson"
    assert "note" in r  # flagged that it may include former players
    assert calls["teams"] == 2


def test_missing_key_returns_error_not_exception(monkeypatch):
    monkeypatch.setenv("BALLDONTLIE_API_KEY", "")
    reset_state(monkeypatch)
    r = run(tools.get_team_roster("Knicks"))
    assert "BALLDONTLIE_API_KEY" in r["error"]


def test_news_without_key(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "")
    assert "TAVILY_API_KEY" in run(tools.search_trade_news("x"))["error"]


# ---- rate limiting, caching and budgets (the "timed out after 15s" bug)

def _healthy_handler(req):
    path = req.url.path
    if path == "/v1/players/active":
        return httpx.Response(200, json={"data": [JOKIC]})
    if path == "/v1/season_averages":
        return httpx.Response(401)
    if path == "/v1/stats":
        return httpx.Response(200, json={"data": [{"min": "36", "pts": 29, "game": {"postseason": False}}], "meta": {}})
    if path == "/nba/v1/player_injuries":
        return httpx.Response(200, json={"data": []})
    return httpx.Response(404)


def test_long_429_fails_fast_without_cascading(monkeypatch):
    def handler(req):
        return httpx.Response(429, headers={"Retry-After": "40"})

    calls = install(monkeypatch, handler)
    r = run(tools.get_player_stats("Nikola Jokic"))
    assert "rate limit" in r["error"]
    assert len(calls) == 1  # no retries or fallbacks piled onto an exhausted quota


def test_rate_limit_after_player_found_still_returns_bio(monkeypatch):
    def handler(req):
        if req.url.path == "/v1/players/active":
            return httpx.Response(200, json={"data": [JOKIC]})
        return httpx.Response(429, headers={"Retry-After": "40"})

    install(monkeypatch, handler)
    r = run(tools.get_player_stats("Nikola Jokic"))
    assert "error" not in r
    assert r["player"] == "Nikola Jokić" and r["stats"] is None
    assert "rate limit" in r["stats_note"]


def test_repeat_lookup_is_served_from_cache(monkeypatch):
    calls = install(monkeypatch, _healthy_handler)
    first = run(tools.get_player_stats("Nikola Jokic"))
    n = len(calls)
    second = run(tools.get_player_stats("Nikola Jokic"))
    assert second["stats"] == first["stats"]
    assert len(calls) == n  # zero new requests


def test_unsupported_endpoints_are_skipped_after_first_failure(monkeypatch):
    calls = install(monkeypatch, _healthy_handler)
    run(tools.get_player_stats("Nikola Jokic", season=2025))
    run(tools.get_player_stats("Nikola Jokic", season=2024))
    assert calls.count("/v1/season_averages") == 1


def test_one_search_call_for_a_normal_name(monkeypatch):
    calls = install(monkeypatch, _healthy_handler)
    run(tools.find_player("Nikola Jokic"))
    assert calls == ["/v1/players/active"]


def test_slow_stats_returns_bio_instead_of_error(monkeypatch):
    import asyncio as aio

    real_sleep = aio.sleep

    async def slow_handler(req):
        if req.url.path == "/v1/players/active":
            return httpx.Response(200, json={"data": [JOKIC]})
        await real_sleep(1)
        return httpx.Response(200, json={"data": []})

    monkeypatch.setenv("BALLDONTLIE_API_KEY", "test")
    reset_state(monkeypatch)
    monkeypatch.setattr(tools, "_http", httpx.AsyncClient(transport=httpx.MockTransport(slow_handler)))
    monkeypatch.setattr(tools, "STATS_BUDGET_SECONDS", 0.2)
    r = run(tools.get_player_stats("Nikola Jokic"))
    assert "error" not in r
    assert "timed out" in r["stats_note"]


def test_minute_window_paces_bursts(monkeypatch):
    clock = {"t": 0.0}
    monkeypatch.setattr(tools.time, "monotonic", lambda: clock["t"])

    async def fake_sleep(d):
        clock["t"] += d

    monkeypatch.setattr(tools.asyncio, "sleep", fake_sleep)

    async def burst():
        w = tools._MinuteWindow(3)
        for _ in range(5):
            await w.acquire()
        return clock["t"]

    elapsed = run(burst())
    assert 60 <= elapsed < 63  # first 3 immediate, the 4th waits for the window to roll
