from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

# In-memory store for now. This resets every time the server restarts
tasks = []
next_id = 1


class Task(BaseModel):
    title: str
    description: str | None = None
    completed: bool = False


@app.get("/")
def health_check():
    return {"status": "ok"}


@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    # Walk the list looking for a matching id, return as soon as we find it.
    for task in tasks:
        if task["id"] == task_id:
            return task

    # Fell out of the loop without a match — that id doesn't exist.
    raise HTTPException(status_code=404, detail="Task not found")


@app.get("/tasks")
def list_tasks():
    return tasks


@app.post("/tasks")
def create_task(task: Task):
    # next_id is a module-level counter, so we need `global` to reassign it.
    global next_id

    # Turn the Pydantic model into a plain dict so we can tack on an id.
    new_task = task.model_dump()
    new_task["id"] = next_id

    tasks.append(new_task)
    next_id += 1  # hand the next task a fresh id

    return new_task


@app.put("/tasks/{task_id}")
def update_task(task_id: int, updated: Task):
    # enumerate gives us the position (index) alongside each task, so we can
    # overwrite the right slot in the list once we find a match.
    for index, task in enumerate(tasks):
        if task["id"] == task_id:
            new_task = updated.model_dump()
            new_task["id"] = task_id  # keep the original id, don't let it change
            tasks[index] = new_task
            return new_task

    raise HTTPException(status_code=404, detail="Task not found")


@app.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    for index, task in enumerate(tasks):
        if task["id"] == task_id:
            tasks.pop(index)  # remove it from the list by position
            return {"message": f"Task {task_id} deleted"}

    raise HTTPException(status_code=404, detail="Task not found")
