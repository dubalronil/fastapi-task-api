from pydantic import BaseModel, ConfigDict


# What a client is allowed to SEND when creating/updating a task.
# Note: no id here — the database assigns that, not the client.
class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    completed: bool = False


# What we SEND BACK to the client. Includes the id the database generated.
class TaskResponse(BaseModel):
    id: int
    title: str
    description: str | None = None
    completed: bool

    # Lets Pydantic build this straight from a SQLAlchemy object by reading
    # its attributes (task.id, task.title, ...) instead of a dict.
    model_config = ConfigDict(from_attributes=True)
