from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime

from .database import Base


class URL(Base):
    __tablename__ = "urls"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        index=True
    )

    original_url = Column(
        String,
        nullable=False
    )

    short_code = Column(
        String,
        unique=True,
        nullable=False,
        index=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    expires_at = Column(
        DateTime,
        nullable=True
    )

    click_count = Column(
        Integer,
        default=0
    )