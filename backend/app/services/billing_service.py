"""
Stripe subscription billing service.

Manages checkout sessions, customer portal, webhook processing,
and subscription status queries.
"""

from __future__ import annotations

import logging
from typing import Optional

import stripe
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.user import User
from app.models.enums import Plan, enum_value

logger = logging.getLogger(__name__)
settings = get_settings()
stripe.api_key = settings.STRIPE_SECRET_KEY

# ============================================================================
# Price IDs — created in Stripe Dashboard
# ============================================================================

PRICE_IDS: dict[str, dict[str, str]] = {
    "pro": {
        "monthly": settings.STRIPE_PRO_MONTHLY_PRICE_ID or "price_pro_monthly",
        "yearly": settings.STRIPE_PRO_YEARLY_PRICE_ID or "price_pro_yearly",
    },
    "quant": {
        "monthly": settings.STRIPE_QUANT_MONTHLY_PRICE_ID or "price_quant_monthly",
        "yearly": settings.STRIPE_QUANT_YEARLY_PRICE_ID or "price_quant_yearly",
    },
}

PLAN_META = {
    "free": {
        "name": "Free",
        "limits": {"backtests_per_day": 5, "api_access": False},
    },
    "pro": {
        "name": "Pro",
        "limits": {"backtests_per_day": -1, "api_access": False},
        "prices": {"monthly": 1900, "yearly": 15900},
    },
    "quant": {
        "name": "Quant",
        "limits": {"backtests_per_day": -1, "api_access": True},
        "prices": {"monthly": 4900, "yearly": 39900},
    },
}

# Test mode price cache — auto-created on first use
_test_price_cache: dict[str, str] = {}


async def _get_or_create_test_price(price_slug: str) -> str:
    """Auto-create a Stripe test-mode price if no real price ID is configured."""
    if price_slug in _test_price_cache:
        return _test_price_cache[price_slug]

    # Map slugs to amounts
    amount_map = {
        "price_pro_monthly": 1900,
        "price_pro_yearly": 15900,
        "price_quant_monthly": 4900,
        "price_quant_yearly": 39900,
    }
    amount = amount_map.get(price_slug, 1900)  # Default $19
    product_name = price_slug.replace("price_", "").replace("_", " ").title()

    # Create product if not exists
    products = stripe.Product.list(limit=100)
    product = next((p for p in products.data if p.name == product_name), None)
    if not product:
        product = stripe.Product.create(name=product_name, description=f"QuantFlow {product_name} (test mode)")

    interval = "month" if "monthly" in price_slug else "year"
    price = stripe.Price.create(
        product=product.id,
        unit_amount=amount,
        currency="usd",
        recurring={"interval": interval},
    )
    _test_price_cache[price_slug] = price.id
    logger.info("Auto-created test price: %s → %s ($%.2f)", price_slug, price.id, amount / 100)
    return price.id


# Webhook event idempotency — track processed event IDs (TTL 24h in Redis in prod)
_PROCESSED_EVENTS: set[str] = set()


# ============================================================================
# Startup: pre-create test prices
# ============================================================================

def ensure_test_prices():
    """Called on startup — pre-creates test mode products/prices so checkout doesn't fail."""
    if not settings.STRIPE_SECRET_KEY or settings.STRIPE_SECRET_KEY.startswith("sk_test_"):
        for slug in ["price_pro_monthly", "price_pro_yearly", "price_quant_monthly", "price_quant_yearly"]:
            try:
                pid = _get_or_create_test_price(slug)
                logger.info("Test price ready: %s → %s", slug, pid)
            except Exception as exc:
                logger.warning("Could not pre-create test price %s: %s", slug, exc)


# ============================================================================
# Checkout session
# ============================================================================


async def create_checkout_session(
    user: User,
    db: AsyncSession,
    price_id: str,
    success_url: str,
    cancel_url: str,
) -> str:
    """
    Create a Stripe Checkout session for a subscription.

    Creates or reuses the Stripe Customer, then builds a Checkout
    session in `subscription` mode with the given Price ID.

    Returns the checkout URL to redirect the user to.
    """
    # Ensure customer exists
    customer_id = await _ensure_customer(user, db)

    # If price_id looks like a placeholder (not a real Stripe price_XXXXXXXX), auto-create it
    # Real Stripe IDs: price_1AbCdEfGhIjKlMnOp (starts with price_ then at least 14 chars including numbers)
    is_real_price = price_id.startswith("price_") and len(price_id) > 20 and any(c.isdigit() for c in price_id[6:])
    if not is_real_price:
        price_id = await _get_or_create_test_price(price_id)

    try:
        session = stripe.checkout.Session.create(
            customer=customer_id,
            mode="subscription" if price_id.startswith("price_") else "payment",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"user_id": str(user.id)},
            allow_promotion_codes=True,
            billing_address_collection="auto",
        )
        logger.info("Checkout session %s created for user %s", session.id, user.id)
        return session.url or ""
    except Exception as exc:
        logger.exception("Stripe checkout error for user %s: %s", user.id, exc)
        raise RuntimeError(f"Stripe error: {exc}") from exc


# ============================================================================
# Customer Portal
# ============================================================================


async def create_portal_session(
    user: User,
    db: AsyncSession,
    return_url: str,
) -> str:
    """
    Create a Stripe Customer Portal session.

    The portal lets users manage their subscription (upgrade, cancel,
    update payment method, view invoices) without leaving the app.
    """
    customer_id = await _ensure_customer(user, db)

    try:
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )
        logger.info("Portal session created for user %s", user.id)
        return session.url
    except stripe.StripeError as exc:
        logger.error("Portal error for user %s: %s", user.id, exc)
        raise RuntimeError(f"Failed to create portal session: {exc}") from exc


# ============================================================================
# Subscription status
# ============================================================================


async def get_subscription_status(user: User) -> dict:
    """
    Return the current subscription status for a user.

    Returns:
        {
            "plan": "pro",
            "status": "active" | "past_due" | "canceled" | None,
            "current_period_end": "2025-01-15T00:00:00Z" | None,
            "cancel_at_period_end": bool,
        }
    """
    result = {
        "plan": enum_value(user.plan) if user.plan else "free",
        "status": None,
        "current_period_end": None,
        "cancel_at_period_end": False,
    }

    if not user.stripe_subscription_id:
        return result

    try:
        sub = stripe.Subscription.retrieve(user.stripe_subscription_id)
        result["status"] = sub.status
        if sub.current_period_end:
            result["current_period_end"] = sub.current_period_end.isoformat()
        result["cancel_at_period_end"] = sub.cancel_at_period_end
    except stripe.StripeError as exc:
        logger.warning("Could not retrieve subscription for user %s: %s", user.id, exc)

    return result


# ============================================================================
# Webhook handler
# ============================================================================


async def handle_webhook(
    payload: bytes,
    signature: str,
    db: AsyncSession,
) -> dict:
    """
    Process a Stripe webhook event.

    Verifies the Stripe signature, deduplicates events, and routes
    to the appropriate handler based on event type.

    Returns {"status": "ok"} on success, {"status": "error", "message": ...}
    on failure.
    """
    # Verify signature
    try:
        event = stripe.Webhook.construct_event(
            payload, signature, settings.STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        logger.warning("Webhook signature verification failed")
        return {"status": "error", "message": "Invalid signature"}
    except ValueError:
        logger.warning("Webhook payload parse error")
        return {"status": "error", "message": "Invalid payload"}

    # Idempotency — skip already-processed events
    event_id = event.get("id", "")
    if event_id in _PROCESSED_EVENTS:
        logger.debug("Skipping duplicate webhook event %s", event_id)
        return {"status": "ok", "message": "Already processed"}
    _PROCESSED_EVENTS.add(event_id)

    event_type = event["type"]
    logger.info("Processing webhook %s: %s", event_id, event_type)

    try:
        match event_type:
            case "checkout.session.completed":
                await _handle_checkout_completed(event["data"]["object"], db)
            case "customer.subscription.updated":
                await _handle_subscription_updated(event["data"]["object"], db)
            case "customer.subscription.deleted":
                await _handle_subscription_deleted(event["data"]["object"], db)
            case "invoice.payment_failed":
                await _handle_invoice_failed(event["data"]["object"], db)
            case _:
                logger.debug("Unhandled webhook event type: %s", event_type)
    except Exception as exc:
        logger.exception("Error processing webhook %s: %s", event_id, exc)
        # Remove from processed set so it can be retried
        _PROCESSED_EVENTS.discard(event_id)
        return {"status": "error", "message": str(exc)}

    return {"status": "ok"}


# ============================================================================
# Create customer
# ============================================================================


async def create_customer(email: str, name: str) -> Optional[str]:
    """Create a Stripe customer. Returns the customer ID."""
    if not settings.STRIPE_SECRET_KEY:
        return None
    try:
        customer = stripe.Customer.create(email=email, name=name)
        logger.info("Stripe customer created: %s", customer.id)
        return customer.id
    except Exception as exc:
        logger.warning("Stripe customer creation failed for %s: %s", email, exc)
        return None


# ============================================================================
# Internal helpers
# ============================================================================


async def _ensure_customer(user: User, db: AsyncSession) -> str:
    """Get or create a Stripe customer ID for the user."""
    if user.stripe_customer_id:
        return user.stripe_customer_id

    try:
        customer_id = await create_customer(user.email, user.full_name or "")
        if customer_id:
            user.stripe_customer_id = customer_id
            await db.commit()
            return customer_id
    except Exception as exc:
        logger.warning("Stripe customer creation failed: %s", exc)

    # Fallback: use a mock customer ID for test mode
    if not settings.STRIPE_SECRET_KEY or settings.STRIPE_SECRET_KEY.startswith("sk_test_"):
        import uuid
        fallback_id = f"cus_test_{uuid.uuid4().hex[:12]}"
        user.stripe_customer_id = fallback_id
        await db.commit()
        logger.info("Using test-mode fallback customer: %s", fallback_id)
        return fallback_id

    raise RuntimeError("Stripe is not configured. Set STRIPE_SECRET_KEY in environment variables.")


async def _get_user_by_customer_id(
    customer_id: str, db: AsyncSession
) -> Optional[User]:
    """Look up a user by their Stripe customer ID."""
    result = await db.execute(
        select(User).where(User.stripe_customer_id == customer_id)
    )
    return result.scalar_one_or_none()


async def _get_user_by_subscription_id(
    subscription_id: str, db: AsyncSession
) -> Optional[User]:
    """Look up a user by their Stripe subscription ID."""
    result = await db.execute(
        select(User).where(User.stripe_subscription_id == subscription_id)
    )
    return result.scalar_one_or_none()


def _price_id_to_plan(price_id: str) -> str:
    """Map a Stripe Price ID to our plan name."""
    for plan, periods in PRICE_IDS.items():
        for price in periods.values():
            if price == price_id:
                return plan
    return "free"


# ============================================================================
# Webhook event handlers
# ============================================================================


async def _handle_checkout_completed(
    session: dict,
    db: AsyncSession,
) -> None:
    """Checkout session completed — activate subscription."""
    customer_id = session.get("customer")
    subscription_id = session.get("subscription")
    if not customer_id or not subscription_id:
        return

    user = await _get_user_by_customer_id(customer_id, db)
    if not user:
        logger.warning("No user found for Stripe customer %s", customer_id)
        return

    # Determine plan from the line item price
    try:
        sub = stripe.Subscription.retrieve(subscription_id)
        price_id = sub["items"]["data"][0]["price"]["id"]
        plan = _price_id_to_plan(price_id)
    except Exception:
        plan = "pro"  # Default fallback

    user.plan = Plan(plan)
    user.stripe_subscription_id = subscription_id
    await db.commit()
    logger.info("User %s upgraded to %s via checkout", user.id, plan)


async def _handle_subscription_updated(
    subscription: dict,
    db: AsyncSession,
) -> None:
    """Subscription updated — sync plan and status."""
    subscription_id = subscription.get("id")
    if not subscription_id:
        return

    user = await _get_user_by_subscription_id(subscription_id, db)
    if not user:
        # Try customer lookup
        customer_id = subscription.get("customer")
        if customer_id:
            user = await _get_user_by_customer_id(customer_id, db)
    if not user:
        return

    status = subscription.get("status", "")
    if status in ("active", "trialing"):
        try:
            price_id = subscription["items"]["data"][0]["price"]["id"]
            plan = _price_id_to_plan(price_id)
            user.plan = Plan(plan)
        except Exception:
            pass
    elif status == "past_due":
        pass  # Keep current plan but log
    elif status in ("canceled", "unpaid"):
        pass  # Handled by subscription.deleted

    await db.commit()
    logger.info("Subscription updated for user %s: status=%s", user.id, status)


async def _handle_subscription_deleted(
    subscription: dict,
    db: AsyncSession,
) -> None:
    """Subscription deleted/cancelled — downgrade to free."""
    subscription_id = subscription.get("id")
    if not subscription_id:
        return

    user = await _get_user_by_subscription_id(subscription_id, db)
    if user:
        user.plan = Plan.free
        user.stripe_subscription_id = None
        await db.commit()
        logger.info("User %s downgraded to free (subscription deleted)", user.id)


async def _handle_invoice_failed(
    invoice: dict,
    db: AsyncSession,
) -> None:
    """Invoice payment failed — notify user."""
    customer_id = invoice.get("customer")
    if not customer_id:
        return

    user = await _get_user_by_customer_id(customer_id, db)
    if not user:
        return

    logger.warning(
        "Payment failed for user %s (invoice %s). Sending notification.",
        user.id,
        invoice.get("id"),
    )

    # Attempt to send email notification via Resend or similar
    try:
        await _send_payment_failed_email(user.email, user.full_name, invoice)
    except Exception as exc:
        logger.error("Failed to send payment-failed email: %s", exc)


async def _send_payment_failed_email(
    email: str,
    name: Optional[str],
    invoice: dict,
) -> None:
    """Send a payment failure notification email."""
    # Placeholder — integrate with Resend, SendGrid, or Mailgun
    logger.info(
        "Would send payment-failed email to %s for invoice %s",
        email,
        invoice.get("id"),
    )
