from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user_id
from app.schemas.tasks import TaskCreateRequest, TaskResponse, TaskStatus, TaskUpdateRequest
from app.services import tasks_service

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(payload: TaskCreateRequest, user_id: str = Depends(get_current_user_id)) -> TaskResponse:
    task = await tasks_service.create_task(
        user_id=user_id,
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        due_at=payload.due_at.isoformat() if payload.due_at else None,
        remind_at=payload.remind_at.isoformat() if payload.remind_at else None,
    )
    return TaskResponse(**task)


@router.get("", response_model=list[TaskResponse])
async def list_tasks(status: TaskStatus | None = None, user_id: str = Depends(get_current_user_id)) -> list[TaskResponse]:
    tasks = await tasks_service.list_tasks(user_id, status=status)
    return [TaskResponse(**t) for t in tasks]


@router.get("/reminders", response_model=list[TaskResponse])
async def list_reminders(user_id: str = Depends(get_current_user_id)) -> list[TaskResponse]:
    tasks = await tasks_service.list_upcoming_reminders(user_id)
    return [TaskResponse(**t) for t in tasks]


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, user_id: str = Depends(get_current_user_id)) -> TaskResponse:
    task = await tasks_service.get_task(user_id, task_id)
    return TaskResponse(**task)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(task_id: str, payload: TaskUpdateRequest, user_id: str = Depends(get_current_user_id)) -> TaskResponse:
    task = await tasks_service.update_task(
        user_id=user_id,
        task_id=task_id,
        title=payload.title,
        description=payload.description,
        status=payload.status,
        priority=payload.priority,
        due_at=payload.due_at.isoformat() if payload.due_at else None,
        remind_at=payload.remind_at.isoformat() if payload.remind_at else None,
    )
    return TaskResponse(**task)


@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: str, user_id: str = Depends(get_current_user_id)) -> None:
    await tasks_service.delete_task(user_id, task_id)
