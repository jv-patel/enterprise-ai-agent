"""
Top-level entry point for running the agent on a user message. This is the
Coordinator Agent: it decides (or accepts an explicit override for) which
specialized agent handles the request, then drives that agent's run.

Responsibilities:
  1. Resolve/create the chat and load recent conversation history (context awareness)
  2. Pull relevant long-term memories for the user's message
  3. Route to a specialized agent (Assistant/Email/Calendar/Research/Vision/Notes/Task)
     and scope the tool registry to that agent's allowed tools
  4. Start an agent_runs row, invoke the LangGraph graph, and mark it complete/failed
  5. Persist the user + assistant messages back into chat_messages
"""
from dataclasses import dataclass

from app.agents.graph import get_agent_graph
from app.agents.router import classify_intent
from app.agents.specialized_agents import get_agent_definition
from app.agents.tools.registry import build_tool_specs
from app.core.logging_config import get_logger
from app.services import agent_log_service, chat_service, memory_service

logger = get_logger(__name__)

MAX_PLAN_ITERATIONS = 5
MAX_TOOL_RETRIES = 2


@dataclass
class AgentRunOutcome:
    run_id: str
    chat_id: str
    answer: str
    status: str
    agent_name: str


async def run_agent(
    *, user_id: str, chat_id: str | None, user_message: str, agent_name: str | None = None
) -> AgentRunOutcome:
    chat = await chat_service.get_or_create_chat(user_id, chat_id, title_hint=user_message)
    resolved_chat_id = chat["id"]

    history = await chat_service.get_recent_messages(resolved_chat_id)

    try:
        memories = await memory_service.search_memories(user_id=user_id, query=user_message)
        memory_context = [m["content"] for m in memories]
    except Exception:  # noqa: BLE001
        # Long-term memory is best-effort context; a lookup failure must never
        # block the agent from answering.
        logger.warning("Memory search failed for user %s; continuing without it", user_id, exc_info=True)
        memory_context = []

    # Coordinator Agent: route to a specialist unless the caller explicitly picked one.
    resolved_agent_key = agent_name or await classify_intent(user_message)
    agent_def = get_agent_definition(resolved_agent_key)

    run = await agent_log_service.start_run(
        user_id=user_id, chat_id=resolved_chat_id, agent_name=agent_def.key, goal=user_message
    )
    run_id = run["id"]

    await agent_log_service.log_step(
        run_id=run_id,
        step_index=0,
        agent_name="coordinator_agent",
        action_type="route",
        detail={"routed_to": agent_def.key, "explicit_override": agent_name is not None},
    )

    await chat_service.append_message(chat_id=resolved_chat_id, user_id=user_id, role="user", content=user_message)

    all_tool_specs = build_tool_specs(user_id=user_id, chat_id=resolved_chat_id)
    tool_specs = (
        all_tool_specs
        if agent_def.tool_names is None
        else [spec for spec in all_tool_specs if spec.name in agent_def.tool_names]
    )

    graph = get_agent_graph()
    initial_state = {
        "user_id": user_id,
        "chat_id": resolved_chat_id,
        "run_id": run_id,
        "agent_name": agent_def.key,
        "system_prompt": agent_def.system_prompt,
        "user_message": user_message,
        "conversation_history": history,
        "long_term_context": memory_context,
        "tool_specs": tool_specs,
        "pending_tool_calls": [],
        "last_tool_results": [],
        "tool_rounds": [],
        "step_index": 0,
        "plan_iterations": 0,
        "retries": {},
        "max_retries": MAX_TOOL_RETRIES,
        "max_plan_iterations": MAX_PLAN_ITERATIONS,
        "final_answer": None,
        "error": None,
    }

    try:
        final_state = await graph.ainvoke(initial_state)
        answer = final_state.get("final_answer") or "I wasn't able to generate a response."
        await agent_log_service.complete_run(run_id=run_id, status="completed")
        status = "completed"
    except Exception as exc:  # noqa: BLE001
        logger.exception("Agent run %s failed", run_id)
        answer = "Something went wrong while processing that request. Please try again."
        await agent_log_service.complete_run(run_id=run_id, status="failed")
        status = "failed"

    await chat_service.append_message(chat_id=resolved_chat_id, user_id=user_id, role="assistant", content=answer)

    return AgentRunOutcome(run_id=run_id, chat_id=resolved_chat_id, answer=answer, status=status, agent_name=agent_def.key)
