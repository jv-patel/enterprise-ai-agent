from fastapi import APIRouter, Depends

from app.agents.coordinator import run_agent
from app.agents.specialized_agents import list_agent_definitions
from app.core.dependencies import get_current_user_id
from app.schemas.agent import (
    AgentDefinitionResponse,
    AgentLogEntry,
    AgentRunRequest,
    AgentRunResponse,
    AgentRunSummary,
)
from app.services import agent_log_service, chat_service

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/chat", response_model=AgentRunResponse)
async def chat_with_agent(payload: AgentRunRequest, user_id: str = Depends(get_current_user_id)) -> AgentRunResponse:
    outcome = await run_agent(
        user_id=user_id, chat_id=payload.chat_id, user_message=payload.message, agent_name=payload.agent_name
    )
    return AgentRunResponse(
        run_id=outcome.run_id,
        chat_id=outcome.chat_id,
        answer=outcome.answer,
        status=outcome.status,
        agent_name=outcome.agent_name,
    )


@router.get("/agents", response_model=list[AgentDefinitionResponse])
async def get_available_agents() -> list[AgentDefinitionResponse]:
    return [
        AgentDefinitionResponse(key=a.key, display_name=a.display_name, description=a.description)
        for a in list_agent_definitions()
    ]


@router.get("/runs", response_model=list[AgentRunSummary])
async def get_agent_runs(chat_id: str | None = None, user_id: str = Depends(get_current_user_id)) -> list[AgentRunSummary]:
    runs = await agent_log_service.list_runs(user_id, chat_id=chat_id)
    return [AgentRunSummary(**run) for run in runs]


@router.get("/runs/{run_id}/timeline", response_model=list[AgentLogEntry])
async def get_agent_run_timeline(run_id: str, user_id: str = Depends(get_current_user_id)) -> list[AgentLogEntry]:
    logs = await agent_log_service.get_run_timeline(run_id, user_id)
    return [AgentLogEntry(**log) for log in logs]


@router.get("/chats")
async def get_chats(user_id: str = Depends(get_current_user_id)) -> list[dict]:
    return await chat_service.list_chats(user_id)
