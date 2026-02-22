import logging
from datetime import datetime, timezone

import stripe
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.user import User

logger = logging.getLogger(__name__)


class StripeService:
    def __init__(self, db: AsyncSession):
        self.db = db
        settings = get_settings()
        stripe.api_key = settings.stripe_secret_key

    async def get_or_create_customer(self, user: User) -> str:
        """Get existing Stripe customer or create a new one."""
        if user.stripe_customer_id:
            return user.stripe_customer_id

        customer = stripe.Customer.create(
            email=user.email,
            name=user.name,
            metadata={"user_id": str(user.id)},
        )
        user.stripe_customer_id = customer.id
        await self.db.commit()
        return customer.id

    async def create_checkout_session(self, user: User, success_url: str, cancel_url: str) -> str:
        """Create a Stripe Checkout session for subscription."""
        settings = get_settings()
        customer_id = await self.get_or_create_customer(user)

        session = stripe.checkout.Session.create(
            customer=customer_id,
            mode="subscription",
            payment_method_types=["card"],
            line_items=[{"price": settings.stripe_price_id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"user_id": str(user.id)},
        )
        return session.url

    async def create_portal_session(self, user: User, return_url: str) -> str:
        """Create a Stripe Customer Portal session to manage subscription."""
        customer_id = await self.get_or_create_customer(user)

        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )
        return session.url

    async def handle_webhook_event(self, payload: bytes, sig_header: str) -> None:
        """Process incoming Stripe webhook events."""
        settings = get_settings()
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.stripe_webhook_secret
            )
        except (ValueError, stripe.error.SignatureVerificationError) as e:
            logger.error(f"Stripe webhook verification failed: {e}")
            raise

        event_type = event["type"]
        data = event["data"]["object"]

        logger.info(f"Processing Stripe webhook: {event_type}")

        if event_type == "checkout.session.completed":
            await self._handle_checkout_completed(data)
        elif event_type == "customer.subscription.updated":
            await self._handle_subscription_updated(data)
        elif event_type == "customer.subscription.deleted":
            await self._handle_subscription_deleted(data)
        elif event_type == "invoice.payment_failed":
            await self._handle_payment_failed(data)

    async def _find_user_by_customer_id(self, customer_id: str) -> User | None:
        result = await self.db.execute(
            select(User).where(User.stripe_customer_id == customer_id)
        )
        return result.scalar_one_or_none()

    async def _handle_checkout_completed(self, session: dict) -> None:
        customer_id = session.get("customer")
        subscription_id = session.get("subscription")

        if not customer_id or not subscription_id:
            return

        user = await self._find_user_by_customer_id(customer_id)
        if not user:
            # Try to find by metadata user_id
            user_id = session.get("metadata", {}).get("user_id")
            if user_id:
                result = await self.db.execute(
                    select(User).where(User.id == int(user_id))
                )
                user = result.scalar_one_or_none()
                if user:
                    user.stripe_customer_id = customer_id

        if user:
            user.stripe_subscription_id = subscription_id
            user.subscription_status = "active"
            await self.db.commit()
            logger.info(f"Subscription activated for user {user.email}")

    async def _handle_subscription_updated(self, subscription: dict) -> None:
        customer_id = subscription.get("customer")
        if not customer_id:
            return

        user = await self._find_user_by_customer_id(customer_id)
        if user:
            user.subscription_status = subscription["status"]
            user.stripe_subscription_id = subscription["id"]
            await self.db.commit()
            logger.info(f"Subscription updated for user {user.email}: {subscription['status']}")

    async def _handle_subscription_deleted(self, subscription: dict) -> None:
        customer_id = subscription.get("customer")
        if not customer_id:
            return

        user = await self._find_user_by_customer_id(customer_id)
        if user:
            user.subscription_status = "canceled"
            await self.db.commit()
            logger.info(f"Subscription canceled for user {user.email}")

    async def _handle_payment_failed(self, invoice: dict) -> None:
        customer_id = invoice.get("customer")
        if not customer_id:
            return

        user = await self._find_user_by_customer_id(customer_id)
        if user:
            user.subscription_status = "past_due"
            await self.db.commit()
            logger.info(f"Payment failed for user {user.email}")
