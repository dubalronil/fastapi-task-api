from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db

# A mini-app for everything under /tasks. `prefix` is prepended to every
# route below, and `tags` groups them together in the /docs page.
router = APIRouter(prefix="/tasks", tags=["tasks"])


# Fetch a task by id, or raise a 404. Shared by the single-task endpoints.
def get_task_or_404(task_id: int, db: Session) -> models.Task:
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("", response_model=list[schemas.TaskResponse])
def list_tasks(
    completed: bool | None = None,
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
):
    query = db.query(models.Task)

    # Only filter by completed if the client actually asked for it.
    if completed is not None:
        query = query.filter(models.Task.completed == completed)

    # skip/limit implement pagination so we never dump the whole table.
    return query.offset(skip).limit(limit).all()


@router.get("/{task_id}", response_model=schemas.TaskResponse)
def get_task(task_id: int, db: Session = Depends(get_db)):
    return get_task_or_404(task_id, db)


@router.post("", response_model=schemas.TaskResponse, status_code=201)
def create_task(task: schemas.TaskCreate, db: Session = Depends(get_db)):
    # Build a SQLAlchemy Task from the incoming data, then persist it.
    new_task = models.Task(**task.model_dump())
    db.add(new_task)
    db.commit()
    db.refresh(new_task)  # reload so new_task.id is populated
    return new_task


@router.put("/{task_id}", response_model=schemas.TaskResponse)
def update_task(task_id: int, updated: schemas.TaskCreate, db: Session = Depends(get_db)):
    task = get_task_or_404(task_id, db)

    task.title = updated.title
    task.description = updated.description
    task.completed = updated.completed
    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = get_task_or_404(task_id, db)

    db.delete(task)
    db.commit()
    return {"message": f"Task {task_id} deleted"}
