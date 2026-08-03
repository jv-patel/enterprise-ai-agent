"""Task management + reminder tools, bound to the current user via closures."""
from app.agents.tools.registry import ToolSpec
from app.services import tasks_service


def build_task_tools(*, user_id: str) -> list[ToolSpec]:
    async def create_task(
        title: str,
        description: str | None = None,
        priority: str = "medium",
        due_at: str | None = None,
        remind_at: str | None = None,
    ) -> dict:
        task = await tasks_service.create_task(
            user_id=user_id, title=title, description=description, priority=priority, due_at=due_at, remind_at=remind_at
        )
        return {"task_id": task["id"], "title": task["title"], "status": task["status"]}

    async def list_tasks(status: str | None = None) -> dict:
        tasks = await tasks_service.list_tasks(user_id, status=status)
        return {
            "tasks": [
                {"id": t["id"], "title": t["title"], "status": t["status"], "due_at": t["due_at"]}
                for t in tasks
            ]
        }

    async def update_task(
        task_id: str,
        title: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        due_at: str | None = None,
        remind_at: str | None = None,
    ) -> dict:
        task = await tasks_service.update_task(
            user_id=user_id, task_id=task_id, title=title, status=status, priority=priority, due_at=due_at, remind_at=remind_at
        )
        return {"task_id": task["id"], "title": task["title"], "status": task["status"]}

    async def delete_task(task_id: str) -> dict:
        await tasks_service.delete_task(user_id, task_id)
        return {"deleted": True, "task_id": task_id}

    async def list_reminders() -> dict:
        tasks = await tasks_service.list_upcoming_reminders(user_id)
        return {
            "reminders": [
                {"id": t["id"], "title": t["title"], "remind_at": t["remind_at"]} for t in tasks
            ]
        }

    return [
        ToolSpec(
            name="create_task",
            description="Create a new task for the user, optionally with a due date and/or reminder time.",
            parameters={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Task title."},
                    "description": {"type": "string", "description": "Optional task description."},
                    "priority": {"type": "string", "enum": ["low", "medium", "high"], "description": "Task priority."},
                    "due_at": {"type": "string", "description": "ISO 8601 due date/time, if any."},
                    "remind_at": {"type": "string", "description": "ISO 8601 reminder date/time, if any."},
                },
                "required": ["title"],
            },
            handler=create_task,
        ),
        ToolSpec(
            name="list_tasks",
            description="List the user's tasks, optionally filtered by status.",
            parameters={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["pending", "in_progress", "completed", "cancelled"],
                        "description": "Optional status filter.",
                    }
                },
                "required": [],
            },
            handler=list_tasks,
        ),
        ToolSpec(
            name="update_task",
            description="Update a task's title, status, priority, due date, or reminder time.",
            parameters={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "ID of the task to update."},
                    "title": {"type": "string"},
                    "status": {"type": "string", "enum": ["pending", "in_progress", "completed", "cancelled"]},
                    "priority": {"type": "string", "enum": ["low", "medium", "high"]},
                    "due_at": {"type": "string", "description": "ISO 8601 due date/time."},
                    "remind_at": {"type": "string", "description": "ISO 8601 reminder date/time."},
                },
                "required": ["task_id"],
            },
            handler=update_task,
        ),
        ToolSpec(
            name="delete_task",
            description="Delete a task by its ID.",
            parameters={
                "type": "object",
                "properties": {"task_id": {"type": "string", "description": "ID of the task to delete."}},
                "required": ["task_id"],
            },
            handler=delete_task,
        ),
        ToolSpec(
            name="list_reminders",
            description="List the user's upcoming reminders (tasks with a remind_at set).",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=list_reminders,
        ),
    ]
