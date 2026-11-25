# Trade Impact Agent: backend

## Setup
```bash
cd backend
cp .env.example .env   # fill in your 3 keys
pip install -r requirements.txt
python main.py          # http://localhost:8000 (or $PORT)
```

## Endpoints
- `GET /health`: status, current season, models, and which API keys are configured
- `POST /analyze`: `{"team": "Lakers", "trade_description": "..."}` -> full report, blocking
- `POST /analyze/stream`: same body, SSE stream

### Stream events
| event | data |
|---|---|
| `status` | `{message}`: what the agent is doing |
| `tool` | `{id, name, input, status: running\|ok\|error, summary?, ms?}` |
| `player` | one player's raw stats, as soon as the lookup finishes |
| `players` / `sources` | final deduped lists |
| `report` | the normalized report |
| `error` | `{message}`: human-readable failure |
| `done` | `{elapsed_ms}`: always the last event |

Errors: `422` invalid body, `429` per-IP rate limit, `503` all run slots busy.

## Quick test
```bash
curl -N -X POST localhost:8000/analyze/stream \
  -H "Content-Type: application/json" \
  -d '{"team": "Lakers", "trade_description": "LeBron James signs with the Mavericks"}'
```

## Tests
```bash
pip install -r requirements-dev.txt && pytest -q
```
Fully offline: the Claude client is faked and balldontlie is served from a mock transport.
