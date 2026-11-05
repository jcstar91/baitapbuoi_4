from .database import Base
from sqlalchemy import Integer, String, Date, DateTime, ForeignKey, Text, Boolean, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, date, timezone


def now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

class Ticket(Base):
    __tablename__ = "tickets"
    # The queue endpoint filters by status and sorts by deadline, so index both together.
    __table_args__ = (Index("ix_tickets_status_deadline", "status", "deadline_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    received_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Lifecycle: new -> extracted | failed -> queued
    status: Mapped[str] = mapped_column(String(20), default="new", server_default="new")
    raw_message: Mapped[str] = mapped_column(Text, nullable=True)
    
    intent: Mapped[str] = mapped_column(String(100), nullable=True)
    severity: Mapped[str] = mapped_column(String(100), nullable=True)
    product: Mapped[str] = mapped_column(String(100), nullable=True)
    summary : Mapped[str] = mapped_column(String(200), nullable=True)
    needs_human_review: Mapped[bool] = mapped_column(Boolean, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    