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


def install(monkeypatch, handler):
    monkeypatch.setenv("BALLDONTLIE_API_KEY", "test")
    monkeypatch.setattr(tools, "_http", httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    monkeypatch.setattr(tools, "_teams_cache", None)
    monkeypatch.setattr(tools.asyncio, "sleep", _nosleep)


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
    monkeypatch.setattr(tools, "_teams_cache", None)
    r = run(tools.get_team_roster("Knicks"))
    assert "BALLDONTLIE_API_KEY" in r["error"]


def test_news_without_key(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "")
    assert "TAVILY_API_KEY" in run(tools.search_trade_news("x"))["error"]
