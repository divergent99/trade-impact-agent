"""
Trade Impact Agent — LangGraph graph definition.

Speed notes:
- gather_node uses Haiku (fast, cheap, good enough for tool orchestration).
  finalize_node uses Sonnet (slower, but this is where analysis quality matters).
- Multiple tool_use blocks from a single Claude turn are executed concurrently
  via asyncio.gather, not one at a time.
- System prompt + tool schemas are cached (cache_control) since they're an
  identical prefix resent on every turn as the conversation grows.
"""
import asyncio
import json
import os
from typing import TypedDict, Annotated
import operator

from anthropic import AsyncAnthropic
from langgraph.graph import StateGraph, END

from tools import TOOL_SCHEMAS, TOOL_FUNCTIONS

client = AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"), timeout=25.0)

GATHER_MODEL = "claude-haiku-4-5-20251001"
FINALIZE_MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """You are a sharp, slightly opinionated NBA front-office analyst.
Given a trade or roster move, use the available tools to gather real rosters,
player stats, recent news, and injury status, then form a grounded opinion.

Always check stats for the player(s) actually named in the move, AND at
least one other key/star player already on the roster whose fit or role is
most affected by this move (e.g. a similar position, an existing franchise
player, someone whose usage or role changes). This is how a real front
office would evaluate it — never just look up the traded player in
isolation.

Speed matters: when you need multiple independent pieces of information
(e.g. both teams' rosters, or two different players' stats), request ALL of
those tool calls together in a single turn rather than one at a time. Only
make sequential calls when a later call genuinely depends on an earlier
result.

Be concrete: cite actual stats and roster context you pulled, not vague takes.
If a key player has a current injury, factor that into your grade and verdict —
a team acquiring an injured star is a materially different trade than a
healthy one. If this move strongly echoes a real past NBA trade or signing,
name it in historical_parallel — but only if there's a genuinely apt one;
leave it out rather than forcing a weak comparison. Aim for 2-4 tool calls
total, then stop and call finalize_report."""

SYSTEM_BLOCKS = [{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}]

FINALIZE_TOOL = {
    "name": "finalize_report",
    "description": "Submit the final trade impact analysis. Call this once you have enough context.",
    "input_schema": {
        "type": "object",
        "properties": {
            "headline": {"type": "string", "description": "One punchy sentence summarizing the verdict"},
            "trade_grade": {"type": "string", "enum": ["A", "B", "C", "D", "F"]},
            "win_prob_delta": {
                "type": "number",
                "description": "Estimated change in team's win probability / outlook, as a percentage point, can be negative",
            },
            "roster_fit_summary": {"type": "string", "description": "2-3 sentences on how this changes roster construction"},
            "key_stat_comparisons": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "stat": {"type": "string"},
                        "before": {"type": "string"},
                        "after": {"type": "string"},
                    },
                    "required": ["stat", "before", "after"],
                },
            },
            "verdict": {"type": "string", "description": "Full analyst take, 3-5 sentences"},
            "historical_parallel": {
                "type": "string",
                "description": "One sentence drawing a parallel to a genuinely similar real NBA trade or signing from history. Omit entirely if no strong comparison exists — do not force a weak one.",
            },
        },
        "required": ["headline", "trade_grade", "win_prob_delta", "roster_fit_summary", "verdict"],
    },
}


class AgentState(TypedDict):
    messages: Annotated[list, operator.add]
    progress: Annotated[list, operator.add]
    report: dict
    collected_players: Annotated[list, operator.add]
    collected_sources: Annotated[list, operator.add]


TOOL_TIMEOUT_SECONDS = 12


async def gather_node(state: AgentState) -> dict:
    response = await client.messages.create(
        model=GATHER_MODEL,
        max_tokens=1024,
        system=SYSTEM_BLOCKS,
        tools=TOOL_SCHEMAS,
        messages=state["messages"],
    )

    new_messages = [{"role": "assistant", "content": response.content}]
    progress = []
    collected_players = []
    collected_sources = []

    tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

    if tool_use_blocks:
        for block in tool_use_blocks:
            progress.append(f"Calling {block.name}({json.dumps(block.input)})")

        async def run_tool(block):
            fn = TOOL_FUNCTIONS.get(block.name)
            try:
                if not fn:
                    result = {"error": "unknown tool"}
                else:
                    result = await asyncio.wait_for(fn(**block.input), timeout=TOOL_TIMEOUT_SECONDS)
            except asyncio.TimeoutError:
                result = {"error": f"{block.name} timed out after {TOOL_TIMEOUT_SECONDS}s — network may be blocking this API"}
            except Exception as e:
                result = {"error": str(e)}
            return block, result

        # run every tool call from this turn concurrently instead of sequentially
        pairs = await asyncio.gather(*(run_tool(b) for b in tool_use_blocks))

        tool_results = []
        for block, result in pairs:
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result),
                }
            )
            # capture raw player stats untouched by the LLM, for the dashboard —
            # these are ground-truth numbers, not something we want Claude
            # transcribing by hand into the report where it could slip
            if block.name == "get_player_stats" and not result.get("error"):
                collected_players.append(
                    {
                        "name": result.get("player"),
                        "team": result.get("team"),
                        "position": result.get("position"),
                        "season": result.get("season"),
                        "stats": result.get("stats"),
                        "height": result.get("height"),
                        "weight": result.get("weight"),
                        "college": result.get("college"),
                        "draft_year": result.get("draft_year"),
                        "draft_round": result.get("draft_round"),
                        "draft_number": result.get("draft_number"),
                        "stats_note": result.get("stats_note"),
                        "injury": result.get("injury"),
                    }
                )
            # capture article sources for citation display — title + link
            # only, never the article content itself (copyright)
            if block.name == "search_trade_news" and not result.get("error"):
                for src in result.get("sources", []):
                    if src.get("title") and src.get("url"):
                        collected_sources.append({"title": src["title"], "url": src["url"]})

        new_messages.append({"role": "user", "content": tool_results})
    else:
        progress.append("Wrapping up analysis...")

    return {
        "messages": new_messages,
        "progress": progress,
        "collected_players": collected_players,
        "collected_sources": collected_sources,
    }


def should_continue(state: AgentState) -> str:
    last = state["messages"][-1]
    if last["role"] == "user" and isinstance(last["content"], list):
        # last message was tool results -> keep gathering
        return "gather"
    return "finalize"


async def finalize_node(state: AgentState) -> dict:
    # Conversation may currently end on an assistant turn (gather_node's last
    # text reply before it stopped calling tools). Claude requires the message
    # list to end on `user`, so append a closing instruction.
    closing_msg = {
        "role": "user",
        "content": "Based on everything gathered above, call finalize_report now.",
    }
    messages = state["messages"] + [closing_msg]
    response = await client.messages.create(
        model=FINALIZE_MODEL,
        max_tokens=1024,
        system=SYSTEM_BLOCKS,
        tools=[FINALIZE_TOOL],
        tool_choice={"type": "tool", "name": "finalize_report"},
        messages=messages,
    )
    block = next(b for b in response.content if b.type == "tool_use")
    return {
        "messages": [closing_msg, {"role": "assistant", "content": response.content}],
        "progress": ["Report ready."],
        "report": block.input,
    }


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("gather", gather_node)
    graph.add_node("finalize", finalize_node)
    graph.set_entry_point("gather")
    graph.add_conditional_edges("gather", should_continue, {"gather": "gather", "finalize": "finalize"})
    graph.add_edge("finalize", END)
    return graph.compile()


AGENT = build_graph()


def initial_state(team: str, trade_description: str) -> AgentState:
    user_prompt = (
        f"Analyze this move for the {team}: {trade_description}\n\n"
        f"Pull the current roster, relevant player stats, and recent news before forming your verdict."
    )
    return {
        "messages": [{"role": "user", "content": user_prompt}],
        "progress": [],
        "report": {},
        "collected_players": [],
        "collected_sources": [],
    }