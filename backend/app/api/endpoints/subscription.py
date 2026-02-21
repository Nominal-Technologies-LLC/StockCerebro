from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.config import get_settings
from app.database import get_db
from app.models.user import User
from app.schemas.subscription import (
    CheckoutSessionRequest,
    CheckoutSessionResponse,
    PortalSessionRequest,
    PortalSessionResponse,
    SubscriptionStatus,
)
from app.services.stripe_service import StripeService

router = APIRouter(prefix="/api/subscription", tags=["subscription"])


def _get_subscription_status(user: User, is_admin: bool) -> SubscriptionStatus:
    """Compute subscription status for a user."""
    if is_admin:
        access = "admin"
    else:
        access = user.effective_access

    has_access = access in ("admin", "override", "paid", "trialing")
    has_macro_access = access in ("admin", "override", "paid")

    return SubscriptionStatus(
        status=access,
        is_admin=is_admin,
        has_access=has_access,
        has_macro_access=has_macro_access,
        trial_ends_at=user.trial_ends_at,
        subscription_override=user.subscription_override,
    )


@router.get("/status", response_model=SubscriptionStatus)
async def get_subscription_status(
    current_user: User = Depends(get_current_user),
):
    """Get the current user's subscription status."""
    settings = get_settings()
    is_admin = settings.is_admin(current_user.email)
    return _get_subscription_status(current_user, is_admin)


@router.post("/create-checkout-session", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    request: CheckoutSessionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a Stripe Checkout session for subscribing."""
    stripe_service = StripeService(db)
    try:
        checkout_url = await stripe_service.create_checkout_session(
            user=current_user,
            success_url=request.success_url,
            cancel_url=request.cancel_url,
        )
        return CheckoutSessionResponse(checkout_url=checkout_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create checkout session: {e}")


@router.post("/create-portal-session", response_model=PortalSessionResponse)
async def create_portal_session(
    request: PortalSessionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a Stripe Customer Portal session to manage subscription."""
    stripe_service = StripeService(db)
    try:
        portal_url = await stripe_service.create_portal_session(
            user=current_user,
            return_url=request.return_url,
        )
        return PortalSessionResponse(portal_url=portal_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create portal session: {e}")


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events. No auth required - verified via signature."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing stripe-signature header")

    # Use a fresh db session for webhook processing
    from app.database import async_session
    async with async_session() as db:
        stripe_service = StripeService(db)
        try:
            await stripe_service.handle_webhook_event(payload, sig_header)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Webhook error: {e}")

    return JSONResponse(content={"status": "ok"})
