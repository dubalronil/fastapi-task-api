from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

# A mini-app for everything under /tasks. `prefix` is prepended to every
# route below, and `tags` groups them together in the /docs page.
router = APIRouter(prefix="/tasks", tags=["tasks"])

# ge=1 because ids start at 1, so anything lower can't match a row.
TaskId = Annotated[int, Path(ge=1)]

DbSession = Annotated[Session, Depends(get_db)]


# Fetch a task by id, or raise a 404. Shared by the single-task endpoints.
def get_task_or_404(task_id: int, db: Session) -> models.Task:
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("", response_model=list[schemas.TaskResponse])
def list_tasks(
    db: DbSession,
    completed: bool | None = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    # le=100 matters most here. Without a ceiling, ?limit=999999 would make us
    # load the whole table.
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
):
    query = db.query(models.Task)

    # Only filter by completed if the client actually asked for it.
    if completed is not None:
        query = query.filter(models.Task.completed == completed)

    # skip/limit implement pagination so we never dump the whole table.
    # order_by makes the pages deterministic: without ORDER BY the database is
    # free to return rows in any order, so pages could skip or repeat rows.
    return query.order_by(models.Task.id).offset(skip).limit(limit).all()


@router.get("/{task_id}", response_model=schemas.TaskResponse)
def get_task(task_id: TaskId, db: DbSession):
    return get_task_or_404(task_id, db)


@router.post("", response_model=schemas.TaskResponse, status_code=201)
def create_task(task: schemas.TaskCreate, db: DbSession):
    # Build a SQLAlchemy Task from the incoming data, then persist it.
    new_task = models.Task(**task.model_dump())
    db.add(new_task)
    db.commit()
    db.refresh(new_task)  # reload so the id and timestamps are populated
    return new_task


@router.put("/{task_id}", response_model=schemas.TaskResponse)
def replace_task(task_id: TaskId, replacement: schemas.TaskReplace, db: DbSession):
    task = get_task_or_404(task_id, db)

    # No exclude_unset here, unlike PATCH. TaskReplace has no optional fields,
    # so every key is present and overwriting all of them is what PUT means.
    for field, value in replacement.model_dump().items():
        setattr(task, field, value)

    db.commit()
    db.refresh(task)
    return task


@router.patch("/{task_id}", response_model=schemas.TaskResponse)
def update_task(task_id: TaskId, changes: schemas.TaskUpdate, db: DbSession):
    task = get_task_or_404(task_id, db)

    # exclude_unset gives back only the keys the client actually sent, not the
    # ones Pydantic filled in from defaults. So a field left out never gets
    # assigned, and an empty body is a no-op.
    for field, value in changes.model_dump(exclude_unset=True).items():
        setattr(task, field, value)

    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: TaskId, db: DbSession):
    # 204 No Content, so no response body. There is nothing useful to say
    # beyond "it worked", and the old {"message": ...} was a third response
    # shape for clients to handle.
    task = get_task_or_404(task_id, db)

    db.delete(task)
    db.commit()
