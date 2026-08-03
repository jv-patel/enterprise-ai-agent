"""
The Coordinator Agent's routing brain: classifies a user message into one of
the specialized agents using a constrained Gemini call. Falls back to the
general-purpose Assistant Agent on any ambiguity or classification failure —
routing should never be the reason a request fails.
"""
from app.agents.specialized_agents import ASSISTANT_AGENT, SPECIALIZED_AGENTS, list_agent_definitions
from app.core.logging_config import get_logger
from app.services import gemini_service

logger = get_logger(__name__)

_ROUTER_SYSTEM_PROMPT = """You are a routing classifier for a multi-agent AI system. Given a user's \
message, decide which single specialist agent should handle it.

Available agents:
{agent_list}

Respond with ONLY the exact agent key from the list above — nothing else, no \
punctuation, no explanation. If the request spans multiple areas or doesn't \
clearly match a specialist, respond with "assistant_agent".
"""


def _build_router_prompt() -> str:
    lines = [f"- {agent.key}: {agent.description}" for agent in list_agent_definitions()]
    return _ROUTER_SYSTEM_PROMPT.format(agent_list="\n".join(lines))


async def classify_intent(user_message: str) -> str:
    try:
        result = await gemini_service.generate_turn(
            system_instruction=_build_router_prompt(),
            history=[],
            user_message=user_message,
            tool_specs=[],
        )
    except Exception:  # noqa: BLE001
        logger.warning("Intent classification failed; defaulting to assistant_agent", exc_info=True)
        return ASSISTANT_AGENT.key

    candidate = (result.text or "").strip().lower().strip(".")
    if candidate in SPECIALIZED_AGENTS:
        return candidate

    logger.info("Router returned unrecognized agent key %r; defaulting to assistant_agent", candidate)
    return ASSISTANT_AGENT.key
