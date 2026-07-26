from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

TITLE_MAX = 200
DESCRIPTION_MAX = 2000

# The field rules, written once so the schemas below can't drift apart.
Title = Annotated[str, Field(min_length=1, max_length=TITLE_MAX)]
Description = Annotated[str, Field(max_length=DESCRIPTION_MAX)]

# Strips strings before the length checks run, so "   " becomes "" and then
# fails min_length. Input schemas only, never the response.
_STRIP = ConfigDict(str_strip_whitespace=True)


# What a client can send when creating a task. No id here, the database
# assigns that.
class TaskCreate(BaseModel):
    model_config = _STRIP

    title: Title
    description: Description | None = None
    completed: bool = False


# What a client must send to PUT a task. Every field is required, because PUT
# replaces the whole task and a missing field shouldn't reset silently.
class TaskReplace(BaseModel):
    model_config = _STRIP

    title: Title
    # Field() with no default keeps this required even though it can be null.
    description: Description | None = Field()
    completed: bool


# What a client can send to PATCH a task. Everything is optional, so leaving a
# field out means "don't touch it".
class TaskUpdate(BaseModel):
    model_config = _STRIP

    title: Title | None = None
    description: Description | None = None
    completed: bool | None = None

    @model_validator(mode="after")
    def reject_nulls_on_non_nullable_columns(self):
        # Making everything optional also makes {"title": null} possible, and
        # that column is NOT NULL, so it would blow up as a 500. description
        # isn't listed because its column is nullable and null means "clear it".
        # model_fields_set is what tells "sent as null" apart from "not sent".
        for name in ("title", "completed"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} may not be null")
        return self


# What we send back. No constraints here, since these values came from our own
# database rather than from a client.
class TaskResponse(BaseModel):
    # Lets Pydantic build this straight from a SQLAlchemy object by reading
    # its attributes (task.id, task.title, ...) instead of a dict.
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None = None
    completed: bool

    # Not in any input schema, so a client can't set them. SQLite returns
    # these without a timezone offset, so they read as UTC with nothing saying so.
    created_at: datetime
    updated_at: datetime
