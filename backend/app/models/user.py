from datetime import datetime, timedelta, timezone

from sqlalchemy import Boolean, DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

TRIAL_DURATION_DAYS = 7


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("idx_users_google_id", "google_id"),
        Index("idx_users_email", "email"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    google_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    picture: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_login: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Stripe subscription fields
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subscription_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    subscription_override: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    @property
    def is_trialing(self) -> bool:
        if self.trial_ends_at is None:
            return False
        return datetime.now(timezone.utc) < self.trial_ends_at

    @property
    def has_active_subscription(self) -> bool:
        return self.subscription_status in ("active", "trialing")

    @property
    def effective_access(self) -> str:
        """Returns the effective access level: 'admin', 'override', 'paid', 'trialing', 'expired'."""
        if self.subscription_override:
            return "override"
        if self.has_active_subscription:
            return "paid"
        if self.is_trialing:
            return "trialing"
        return "expired"

    def init_trial(self) -> None:
        """Set up the 7-day free trial for a new user."""
        self.trial_ends_at = datetime.now(timezone.utc) + timedelta(days=TRIAL_DURATION_DAYS)
