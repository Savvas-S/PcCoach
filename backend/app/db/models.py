from datetime import datetime, timezone

from sqlalchemy import DateTime, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Build(Base):
    __tablename__ = "builds"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    request_hash: Mapped[str] = mapped_column(String(64), unique=True)
    result: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
        default=lambda: datetime.now(timezone.utc),
    )
