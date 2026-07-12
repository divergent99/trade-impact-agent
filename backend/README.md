# Trade Impact Agent — backend

## Setup
```bash
cd backend
cp .env.example .env   # fill in your 3 keys
pip install -r requirements.txt --break-system-packages
python main.py          # http://localhost:8000
```

## Endpoints
- `GET /health`
- `POST /analyze` — `{"team": "Lakers", "trade_description": "..."}` -> full report, blocking
- `POST /analyze/stream` — same body, SSE stream of `progress` events then a `report` event

## Quick test
```bash
curl -N -X POST localhost:8000/analyze/stream \
  -H "Content-Type: application/json" \
  -d '{"team": "Lakers", "trade_description": "LeBron James signs with the Mavericks"}'
```
