import json
import os
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from agent import AGENT, initial_state

app = FastAPI(title="Trade Impact Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten for prod, fine for a 24h hack
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    team: str
    trade_description: str


@app.get("/health")
def health():
    return {"status": "ok"}


def _dedupe_players(players):
    seen = {}
    for p in players:
        key = (p.get("name") or "").lower()
        if key and key not in seen:
            seen[key] = p
    return list(seen.values())


def _dedupe_sources(sources):
    seen = {}
    for s in sources:
        key = s.get("url")
        if key and key not in seen:
            seen[key] = s
    return list(seen.values())


@app.post("/analyze")
async def analyze(req: AnalyzeRequest):
    """Non-streaming: run the full graph, return the final report."""
    state = initial_state(req.team, req.trade_description)
    final_state = await AGENT.ainvoke(state)
    return {
        "report": final_state["report"],
        "players": _dedupe_players(final_state.get("collected_players", [])),
        "sources": _dedupe_sources(final_state.get("collected_sources", [])),
    }


@app.post("/analyze/stream")
async def analyze_stream(req: AnalyzeRequest):
    """Streaming: emit progress events as the agent works, then player stats and sources, then the final report."""

    async def event_generator():
        state = initial_state(req.team, req.trade_description)
        all_players = []
        all_sources = []
        async for step in AGENT.astream(state):
            for node_name, update in step.items():
                for line in update.get("progress", []):
                    yield {"event": "progress", "data": json.dumps({"node": node_name, "message": line})}
                if update.get("collected_players"):
                    all_players.extend(update["collected_players"])
                if update.get("collected_sources"):
                    all_sources.extend(update["collected_sources"])
                if update.get("report"):
                    yield {"event": "players", "data": json.dumps(_dedupe_players(all_players))}
                    yield {"event": "sources", "data": json.dumps(_dedupe_sources(all_sources))}
                    yield {"event": "report", "data": json.dumps(update["report"])}
        yield {"event": "done", "data": "{}"}

    return EventSourceResponse(event_generator())


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8010, reload=True)