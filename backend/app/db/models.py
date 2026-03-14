from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Component(Base):
    __tablename__ = "components"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category: Mapped[str] = mapped_column(String(30), index=True)
    brand: Mapped[str] = mapped_column(String(100))
    model: Mapped[str] = mapped_column(String(200))
    specs: Mapped[dict] = mapped_column(JSONB, default=dict)
    in_stock: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    affiliate_links: Mapped[list["AffiliateLink"]] = relationship(
        back_populates="component", cascade="all, delete-orphan"
    )


class AffiliateLink(Base):
    __tablename__ = "affiliate_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    component_id: Mapped[int] = mapped_column(
        ForeignKey("components.id", ondelete="CASCADE"), index=True
    )
    store: Mapped[str] = mapped_column(String(30))
    url: Mapped[str] = mapped_column(String(500))
    price_eur: Mapped[float] = mapped_column(Float, nullable=False)
    last_checked: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
        default=lambda: datetime.now(UTC),
    )

    component: Mapped["Component"] = relationship(back_populates="affiliate_links")

    __table_args__ = (
        UniqueConstraint("component_id", "store", name="uq_affiliate_component_store"),
    )


class Build(Base):
    __tablename__ = "builds"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    request_hash: Mapped[str] = mapped_column(String(64), unique=True)
    request: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    result: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
        default=lambda: datetime.now(UTC),
    )
