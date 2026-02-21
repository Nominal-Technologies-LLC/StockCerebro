from datetime import datetime

from pydantic import BaseModel


class SubscriptionStatus(BaseModel):
    status: str  # 'trialing', 'active', 'past_due', 'canceled', 'expired', 'override'
    is_admin: bool
    has_access: bool  # Can use the app (trial, active, admin, override)
    has_macro_access: bool  # Can use macro tab (paid, admin, override only)
    trial_ends_at: datetime | None
    subscription_override: bool


class CheckoutSessionRequest(BaseModel):
    success_url: str
    cancel_url: str


class CheckoutSessionResponse(BaseModel):
    checkout_url: str


class PortalSessionRequest(BaseModel):
    return_url: str


class PortalSessionResponse(BaseModel):
    portal_url: str
