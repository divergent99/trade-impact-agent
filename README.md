# Trade Desk - Live Agent Trade Analysis

Describe an NBA trade or signing. A LangGraph agent pulls real rosters, live stats, injury reports, and breaking news, then grades it like a front-office analyst on deadline — live, in front of you, with the reasoning visible as it happens.

Built for **United Hacks V7** (Sport Track).

<p align="left">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/LangGraph-1C3C3C?style=flat&logo=langchain&logoColor=white" alt="LangGraph" />
  <img src="https://img.shields.io/badge/Claude-Sonnet%20%26%20Haiku-D97757?style=flat&logo=anthropic&logoColor=white" alt="Claude" />
  <img src="https://img.shields.io/badge/React-18-61DAFB?style=flat&logo=react&logoColor=black" alt="React" />
  <img src="https://img.shields.io/badge/Vite-5-646CFF?style=flat&logo=vite&logoColor=white" alt="Vite" />
  <img src="https://img.shields.io/badge/WebGL-OGL-990000?style=flat&logo=webgl&logoColor=white" alt="WebGL" />
  <img src="https://img.shields.io/badge/balldontlie-NBA%20Data-FF7A1A?style=flat" alt="balldontlie" />
  <img src="https://img.shields.io/badge/Tavily-Search-38BDF8?style=flat" alt="Tavily" />
  <img src="https://img.shields.io/badge/License-MIT-4ADE80?style=flat" alt="MIT License" />
</p>

---

## What it does

Type a move — *"LeBron James signs with the Mavericks"* — and pick the team you're evaluating for. An autonomous agent:

1. Pulls the real current roster for both teams involved
2. Looks up season stats **and current injury status** for the traded player plus at least one key incumbent whose fit is affected
3. Searches recent news for trade context and reactions
4. Reasons through it and produces a graded report — letter grade, win-probability delta, stat comparisons, a historical parallel when one genuinely fits, and cited sources

You watch it happen live: a terminal-style feed streams each tool call as the agent makes it, followed by a stat dashboard and the final report card.

The agent decides on its own which players matter enough to check — nobody hand-picks who gets analyzed.

## Architecture

```mermaid
flowchart LR
    subgraph Frontend["Frontend — React + Vite"]
        UI[Trade Form] --> SSE[SSE Stream Consumer]
        SSE --> Feed[Live Agent Feed]
        SSE --> Dash[Player Dashboard]
        SSE --> Report[Report Card]
    end

    subgraph Backend["Backend — FastAPI"]
        API["/analyze/stream"] --> Graph
    end

    subgraph Agent["LangGraph Agent"]
        Graph{{gather}} -->|tool calls| Tools
        Tools --> Graph
        Graph -->|done gathering| Finalize{{finalize}}
    end

    subgraph Tools["Tools (parallel execution)"]
        T1[get_team_roster]
        T2["get_player_stats<br/>+ injury status"]
        T3[search_trade_news]
    end

    subgraph External["External APIs"]
        BDL[(balldontlie<br/>NBA Data)]
        TAV[(Tavily<br/>Web Search)]
        CLD[(Claude API<br/>Haiku + Sonnet)]
    end

    UI -->|POST| API
    SSE -.->|SSE events| API
    Graph <-.-> CLD
    Finalize <-.-> CLD
    T1 <--> BDL
    T2 <--> BDL
    T3 <--> TAV
```

**Design choices worth knowing:**

- **Two models, one graph.** The `gather` node runs on Haiku (fast, cheap, fine for tool orchestration); `finalize` runs on Sonnet (slower, but this is where analysis quality actually matters).
- **Tool calls execute concurrently**, not sequentially — when the agent needs both teams' rosters, it fires both requests at once via `asyncio.gather`.
- **Structured output is forced**, not parsed. The final report is generated via a tool call with `tool_choice` forced to `finalize_report`, guaranteeing valid JSON every time instead of hoping the model formats free text correctly.
- **Three-tier stat fallback.** `season_averages` (highest API tier) → averaging individual game logs ourselves (mid tier) → bio data only (free tier). The app degrades gracefully instead of breaking if a data source isn't available.
- **Raw data bypasses the LLM where it matters.** Player stats and injury status are captured directly from tool results and sent to the frontend as-is — never transcribed by Claude into the report, so the dashboard numbers can't drift from what the API actually returned.

## Tech stack

| Layer | Tech |
|---|---|
| Agent orchestration | LangGraph, Anthropic Claude (Haiku 4.5 + Sonnet 4.6) |
| Backend | FastAPI, Server-Sent Events, async httpx |
| Frontend | React 18, Vite, plain CSS (no framework) |
| Sports data | [balldontlie](https://balldontlie.io) (ALL-STAR tier) |
| News search | [Tavily](https://tavily.com) |
| Visuals | Custom BorderGlow (interactive card glow), Prism (WebGL/OGL background) |

## Project structure

```
trade-impact-agent/
├── backend/
│   ├── agent.py              # LangGraph graph: gather -> finalize
│   ├── tools.py               # balldontlie + Tavily tool implementations
│   ├── main.py                 # FastAPI app, SSE streaming endpoint
│   ├── test_balldontlie.py     # standalone API diagnostic script
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── App.jsx
    │   ├── components/         # TradeForm, LiveFeed, PlayerDashboard, ReportCard,
    │   │                        # Card, BorderGlow, Prism
    │   └── lib/api.js          # hand-rolled SSE client
    └── package.json
```

## Running locally

**Backend**
```bash
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # fill in your 3 API keys
python main.py          # -> http://localhost:8000
```

**Frontend**
```bash
cd frontend
cp .env.example .env    # point VITE_API_URL at your backend
npm install
npm run dev              # -> http://localhost:5173
```

### Environment variables

| Key | Where to get it | Notes |
|---|---|---|
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) | |
| `TAVILY_API_KEY` | [tavily.com](https://tavily.com) | |
| `BALLDONTLIE_API_KEY` | [balldontlie.io](https://balldontlie.io) | Free tier works with reduced fidelity; **ALL-STAR ($9.99/mo)** unlocks real per-game stats and injury data |

## Deployment

Built to deploy as two separate services:

- **Backend -> [Railway](https://railway.app)** — set the 3 environment variables above in the Railway dashboard, Railway auto-detects the FastAPI app via `main.py`.
- **Frontend -> [Vercel](https://vercel.com)** — set `VITE_API_URL` to your deployed Railway backend URL before building.

## License

MIT — see [LICENSE](./LICENSE).
