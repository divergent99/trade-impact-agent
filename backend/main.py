import asyncio
import json
import logging
import os
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

import anthropic  # noqa: E402
from fastapi import FastAPI, HTTPException, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from pydantic import BaseModel, Field, field_validator  # noqa: E402
from sse_starlette.sse import EventSourceResponse  # noqa: E402

from agent import AGENT, FINALIZE_MODEL, GATHER_MODEL, initial_state  # noqa: E402
from tools import bdl_key, close_http_client, current_season, season_label, tavily_key  # noqa: E402

log = logging.getLogger("trade-desk")
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))

RUN_TIMEOUT_SECONDS = float(os.environ.get("RUN_TIMEOUT_SECONDS", "150"))
MAX_CONCURRENT_RUNS = int(os.environ.get("MAX_CONCURRENT_RUNS", "4"))
RATE_LIMIT_PER_HOUR = int(os.environ.get("RATE_LIMIT_PER_HOUR", "20"))  # per client IP, 0 disables
def parse_origins(raw: str) -> list[str]:
    """Browsers send the Origin as scheme://host[:port] with no path or
    trailing slash, and CORS matching is exact. Forgive the usual copy-paste
    slips: whitespace, quotes, trailing slashes, uppercase, a missing scheme."""
    out = []
    for o in raw.split(","):
        o = o.strip().strip("'\"").rstrip("/").lower()
        if not o:
            continue
        if o != "*" and "://" not in o:
            o = "https://" + o
        out.append(o)
    return out or ["*"]


ALLOWED_ORIGINS = parse_origins(os.environ.get("ALLOWED_ORIGINS", "*"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    missing = [k for k, v in {"ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY"), "BALLDONTLIE_API_KEY": bdl_key(), "TAVILY_API_KEY": tavily_key()}.items() if not v]
    if missing:
        log.warning("Missing env vars: %s (related features will degrade)", ", ".join(missing))
    log.info("CORS allowed origins: %s", ALLOWED_ORIGINS)
    yield
    await close_http_client()


app = FastAPI(title="Trade Impact Agent", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

_run_slots = asyncio.Semaphore(MAX_CONCURRENT_RUNS)
_hits: dict[str, deque] = defaultdict(deque)


class AnalyzeRequest(BaseModel):
    team: str = Field(min_length=2, max_length=40)
    trade_description: str = Field(min_length=5, max_length=500)

    @field_validator("team", "trade_description")
    @classmethod
    def strip(cls, v: str) -> str:
        v = " ".join(v.split())
        if not v:
            raise ValueError("must not be blank")
        return v


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _check_rate_limit(request: Request):
    if RATE_LIMIT_PER_HOUR <= 0:
        return
    ip = _client_ip(request)
    now = time.monotonic()
    q = _hits[ip]
    while q and now - q[0] > 3600:
        q.popleft()
    if len(q) >= RATE_LIMIT_PER_HOUR:
        retry = int(3600 - (now - q[0])) + 1
        raise HTTPException(429, f"Rate limit reached. Try again in {retry // 60 + 1} min.", headers={"Retry-After": str(retry)})
    q.append(now)


def _check_capacity():
    if _run_slots.locked():
        raise HTTPException(503, "The trade desk is busy with other analyses. Try again in a few seconds.")


def friendly_error(e: BaseException) -> str:
    if isinstance(e, asyncio.TimeoutError):
        return f"Analysis took longer than {int(RUN_TIMEOUT_SECONDS)}s and was stopped. Try a simpler move."
    if isinstance(e, anthropic.AuthenticationError):
        return "The server's Anthropic API key is missing or invalid."
    if isinstance(e, anthropic.RateLimitError):
        return "Claude is rate limiting this server right now. Try again in a minute."
    if isinstance(e, anthropic.APITimeoutError):
        return "Claude took too long to respond. Try again."
    if isinstance(e, anthropic.APIStatusError) and e.status_code in (500, 502, 503, 529):
        return "Claude is overloaded right now. Try again shortly."
    if isinstance(e, anthropic.APIConnectionError):
        return "Couldn't reach the Claude API from the server."
    return "Something went wrong during the analysis."


def _dedupe(items, key):
    seen = {}
    for it in items:
        k = key(it)
        if k and k not in seen:
            seen[k] = it
    return list(seen.values())


def dedupe_players(players):
    return _dedupe(players, lambda p: (p.get("name") or "").lower())


def dedupe_sources(sources):
    return _dedupe(sources, lambda s: s.get("url"))


def _result_payload(final_state: dict) -> dict:
    return {
        "report": final_state["report"],
        "players": dedupe_players(final_state.get("collected_players", [])),
        "sources": dedupe_sources(final_state.get("collected_sources", [])),
    }


@app.get("/health")
def health():
    season = current_season()
    return {
        "status": "ok",
        "season": season_label(season),
        "models": {"gather": GATHER_MODEL, "finalize": FINALIZE_MODEL},
        "configured": {
            "anthropic": bool(os.environ.get("ANTHROPIC_API_KEY")),
            "balldontlie": bool(bdl_key()),
            "tavily": bool(tavily_key()),
        },
    }


@app.post("/analyze")
async def analyze(req: AnalyzeRequest, request: Request):
    """Non-streaming: run the full graph and return the final report."""
    _check_capacity()
    _check_rate_limit(request)
    async with _run_slots:
        try:
            final_state = await asyncio.wait_for(
                AGENT.ainvoke(initial_state(req.team, req.trade_description), config={"recursion_limit": 25}),
                timeout=RUN_TIMEOUT_SECONDS,
            )
        except Exception as e:
            log.exception("analysis failed")
            raise HTTPException(502, friendly_error(e))
    return _result_payload(final_state)


@app.post("/analyze/stream")
async def analyze_stream(req: AnalyzeRequest, request: Request):
    """SSE stream. Events:
    status {message} | tool {id,name,input,status,summary?,ms?} | player {...}
    players [...] | sources [...] | report {...} | error {message} | done {elapsed_ms}
    """
    _check_capacity()
    _check_rate_limit(request)

    async def event_generator():
        queue: asyncio.Queue = asyncio.Queue()
        started = time.perf_counter()

        def emit(event: str, data):
            queue.put_nowait((event, data))

        async def run():
            async with _run_slots:
                try:
                    final_state = await asyncio.wait_for(
                        AGENT.ainvoke(
                            initial_state(req.team, req.trade_description),
                            config={"configurable": {"emit": emit}, "recursion_limit": 25},
                        ),
                        timeout=RUN_TIMEOUT_SECONDS,
                    )
                    payload = _result_payload(final_state)
                    emit("players", payload["players"])
                    emit("sources", payload["sources"])
                    emit("report", payload["report"])
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    log.exception("stream analysis failed")
                    emit("error", {"message": friendly_error(e)})
                finally:
                    emit("done", {"elapsed_ms": int((time.perf_counter() - started) * 1000)})
                    queue.put_nowait(None)

        task = asyncio.create_task(run())
        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                event, data = item
                yield {"event": event, "data": json.dumps(data, default=str)}
        finally:
            # client disconnected or stream finished: stop spending tokens
            if not task.done():
                task.cancel()

    return EventSourceResponse(event_generator(), ping=15)


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=os.environ.get("RELOAD") == "1")
