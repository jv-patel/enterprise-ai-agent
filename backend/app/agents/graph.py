"""
The core LangGraph agent: a bounded plan/act loop with multi-tool execution,
per-tool retry, and a full execution log written to agent_logs.

Flow:
    START -> plan -> (has tool calls?) -> execute_tools -> plan -> ... -> finalize -> END

`plan` asks Gemini (with the full tool registry bound as native function
declarations) either for a final answer or for one or more tool calls.
`execute_tools` runs every requested tool call concurrently, retries any
that raise, and logs each attempt. The loop is bounded by
`max_plan_iterations` to guarantee termination.
"""
import asyncio
from typing import Any

from langgraph.graph import END, StateGraph

from app.agents.state import AgentState
from app.agents.tools.registry import ToolSpec, get_tool_by_name
from app.core.logging_config import get_logger
from app.services import agent_log_service, gemini_service
from app.services.gemini_service import ToolCallRequest

logger = get_logger(__name__)

AGENT_NAME = "assistant_agent"

SYSTEM_PROMPT_TEMPLATE = """You are the Enterprise AI Personal Agent, a capable and precise assistant.

You have access to tools for calculation, weather, current time/date, web search, \
notes, tasks/reminders, and the user's long-term memory. Use tools whenever they \
would make your answer more accurate, current, or actionable — do not guess at \
information a tool can give you exactly.

When the user shares a durable fact or preference about themselves, save it with \
the save_memory tool. When answering something that might depend on earlier \
conversations, consider using search_memory first.

Relevant long-term memory for this user:
{memory_context}

Be concise, direct, and helpful. When you have enough information to fully answer \
the user, respond in plain text with no further tool calls.
"""


def _build_system_prompt(state: AgentState) -> str:
    memory_lines = state.get("long_term_context") or []
    memory_context = "\n".join(f"- {line}" for line in memory_lines) if memory_lines else "(none yet)"

    override = state.get("system_prompt")
    if override:
        return f"{override}\n\nRelevant long-term memory for this user:\n{memory_context}"

    return SYSTEM_PROMPT_TEMPLATE.format(memory_context=memory_context)


def _agent_name(state: AgentState) -> str:
    return state.get("agent_name") or AGENT_NAME


async def plan_node(state: AgentState) -> dict[str, Any]:
    system_instruction = _build_system_prompt(state)
    step_index = state.get("step_index", 0) + 1
    session = state.get("chat_session")

    if session is None:
        # First planning round: create the chat session and send the user's message.
        session = gemini_service.create_chat_session(
            system_instruction=system_instruction,
            history=state["conversation_history"],
            tool_specs=state["tool_specs"],
        )
        result = await session.send(state["user_message"])
    else:
        # Subsequent rounds: send the previous round's tool results back into
        # the SAME session object, so the SDK preserves thought signatures
        # automatically instead of us reconstructing history by hand.
        message = gemini_service.build_tool_result_message(state.get("last_tool_results", []))
        result = await session.send(message)

    await agent_log_service.log_step(
        run_id=state["run_id"],
        step_index=step_index,
        agent_name=_agent_name(state),
        action_type="plan",
        detail={
            "requested_tools": [tc.name for tc in result.tool_calls],
            "has_final_text": bool(result.text) and not result.tool_calls,
        },
    )

    update: dict[str, Any] = {
        "chat_session": session,
        "step_index": step_index,
        "plan_iterations": state.get("plan_iterations", 0) + 1,
        "pending_tool_calls": result.tool_calls,
    }
    if not result.tool_calls:
        update["final_answer"] = result.text or "I wasn't able to generate a response for that."
    return update


async def _execute_single_tool(
    tool_spec: ToolSpec | None,
    call: ToolCallRequest,
    *,
    run_id: str,
    step_index: int,
    max_retries: int,
    agent_name: str,
) -> dict[str, Any]:
    if tool_spec is None:
        await agent_log_service.log_step(
            run_id=run_id,
            step_index=step_index,
            agent_name=agent_name,
            action_type="error",
            detail={"tool": call.name, "error": "Unknown tool requested by model."},
        )
        return {"name": call.name, "output": None, "error": f"Unknown tool: {call.name}"}

    attempt = 0
    last_error: str | None = None
    while attempt <= max_retries:
        try:
            output = await tool_spec.handler(**call.args)
            await agent_log_service.log_step(
                run_id=run_id,
                step_index=step_index,
                agent_name=agent_name,
                action_type="tool_result",
                detail={"tool": call.name, "args": call.args, "attempt": attempt + 1, "success": True},
            )
            return {"name": call.name, "output": output, "error": None}
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            action_type = "retry" if attempt < max_retries else "error"
            await agent_log_service.log_step(
                run_id=run_id,
                step_index=step_index,
                agent_name=agent_name,
                action_type=action_type,
                detail={
                    "tool": call.name,
                    "args": call.args,
                    "attempt": attempt + 1,
                    "success": False,
                    "error": last_error,
                },
            )
            attempt += 1

    return {"name": call.name, "output": None, "error": last_error}


async def execute_tools_node(state: AgentState) -> dict[str, Any]:
    step_index = state["step_index"]
    max_retries = state.get("max_retries", 2)
    tool_specs: list[ToolSpec] = state["tool_specs"]
    calls: list[ToolCallRequest] = state["pending_tool_calls"]
    agent_name = _agent_name(state)

    await agent_log_service.log_step(
        run_id=state["run_id"],
        step_index=step_index,
        agent_name=agent_name,
        action_type="tool_call",
        detail={"tools": [{"name": c.name, "args": c.args} for c in calls]},
    )

    results = await asyncio.gather(
        *[
            _execute_single_tool(
                get_tool_by_name(tool_specs, call.name),
                call,
                run_id=state["run_id"],
                step_index=step_index,
                max_retries=max_retries,
                agent_name=agent_name,
            )
            for call in calls
        ]
    )

    tool_rounds = list(state.get("tool_rounds", []))
    tool_rounds.append({"tool_calls": calls, "tool_results": list(results)})

    return {"tool_rounds": tool_rounds, "last_tool_results": list(results)}


async def finalize_node(state: AgentState) -> dict[str, Any]:
    final_answer = state.get("final_answer")
    if not final_answer:
        final_answer = "I hit a limit while working through this request. Here's what I found so far — let me know if you'd like me to keep going."

    await agent_log_service.log_step(
        run_id=state["run_id"],
        step_index=state.get("step_index", 0) + 1,
        agent_name=_agent_name(state),
        action_type="final_answer",
        detail={"answer": final_answer},
    )
    return {"final_answer": final_answer}


def _should_execute_tools(state: AgentState) -> str:
    if state.get("pending_tool_calls"):
        return "execute_tools"
    return "finalize"


def _should_continue_planning(state: AgentState) -> str:
    if state.get("plan_iterations", 0) >= state.get("max_plan_iterations", 5):
        return "finalize"
    return "plan"


def build_agent_graph():
    graph = StateGraph(AgentState)
    graph.add_node("plan", plan_node)
    graph.add_node("execute_tools", execute_tools_node)
    graph.add_node("finalize", finalize_node)

    graph.set_entry_point("plan")
    graph.add_conditional_edges("plan", _should_execute_tools, {"execute_tools": "execute_tools", "finalize": "finalize"})
    graph.add_conditional_edges("execute_tools", _should_continue_planning, {"plan": "plan", "finalize": "finalize"})
    graph.add_edge("finalize", END)

    return graph.compile()


_COMPILED_GRAPH = None


def get_agent_graph():
    global _COMPILED_GRAPH
    if _COMPILED_GRAPH is None:
        _COMPILED_GRAPH = build_agent_graph()
    return _COMPILED_GRAPH
