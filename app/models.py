from sqlalchemy import Boolean, Column, DateTime, Integer, String, func

from app.database import Base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)

    # nullable=False blocks NULL but still allows "", which is why schemas.py
    # also sets min_length=1.
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    completed = Column(Boolean, default=False, nullable=False)

    # server_default instead of default, so the database sets the time rather
    # than whichever app server happened to handle the request.
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # onupdate only fires when SQLAlchemy actually sends an UPDATE, so a write
    # that changes nothing leaves this alone.
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
