"""Retrieval feedback data model for relevance marking."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Integer, ForeignKey, Text, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


class RetrievalFeedback(Base):
    __tablename__ = "retrieval_feedbacks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("messages.id"), nullable=False)
    knowledge_base_id: Mapped[int] = mapped_column(ForeignKey("knowledge_bases.id"), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    is_relevant: Mapped[bool] = mapped_column(Boolean, nullable=False)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
