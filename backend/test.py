"""
Quick standalone test of the balldontlie API — run this directly to see
exactly what the API returns, no agent/LLM involved.

Usage:
    python test_balldontlie.py
"""
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ.get("BALLDONTLIE_API_KEY", "")
BASE = "https://api.balldontlie.io/v1"
HEADERS = {"Authorization": API_KEY}


def check_key():
    print(f"Using key: {API_KEY[:8]}..." if API_KEY else "NO KEY SET IN .env")
    print("-" * 60)


def find_player(name):
    print(f"Searching for player: {name}")
    resp = httpx.get(f"{BASE}/players", headers=HEADERS, params={"search": name, "per_page": 5})
    print(f"  Status: {resp.status_code}")
    print(f"  Full response: {resp.text}")
    if resp.status_code != 200:
        return None
    data = resp.json().get("data", [])
    if not data:
        print("  No players found.")
        return None
    for p in data:
        print(f"  Found: {p['first_name']} {p['last_name']} (id={p['id']}, team={p.get('team', {}).get('full_name')})")
    return data[0]["id"]


def list_any_players():
    print("Fetching players with NO search filter (sanity check that the API/key works at all)")
    resp = httpx.get(f"{BASE}/players", headers=HEADERS, params={"per_page": 3})
    print(f"  Status: {resp.status_code}")
    print(f"  Full response: {resp.text}")


def get_season_averages(player_id, season=2024):
    print(f"\nFetching season_averages for player_id={player_id}, season={season}")
    resp = httpx.get(
        f"{BASE}/season_averages",
        headers=HEADERS,
        params={"season": season, "player_id": player_id},
    )
    print(f"  Status: {resp.status_code}")
    print(f"  Raw response: {resp.text}")


if __name__ == "__main__":
    check_key()
    list_any_players()
    print()
    pid = find_player("LeBron James")
    if not pid:
        print()
        pid = find_player("LeBron")
    if not pid:
        print()
        pid = find_player("James")
    if pid:
        get_season_averages(pid, season=2024)
        get_season_averages(pid, season=2023)  # try prior season too, in case 2024 just isn't populated yet

    print("\n" + "=" * 60)
    print("Testing the ALL-STAR fallback (averaging from /stats game logs)")
    print("=" * 60)
    import asyncio
    from tools import _find_player, _average_from_game_logs, get_player_stats

    async def test_averaging():
        async with httpx.AsyncClient(timeout=15) as client:
            player = await _find_player(client, "LeBron James")
            if not player:
                print("  Could not find LeBron James")
                return
            averaged = await _average_from_game_logs(client, player["id"], 2024)
            print(f"  Averaged stats for {player['first_name']} {player['last_name']}: {averaged}")

        print("\n  Full get_player_stats() result:")
        result = await get_player_stats("LeBron James", 2024)
        print(f"  {result}")

    asyncio.run(test_averaging())