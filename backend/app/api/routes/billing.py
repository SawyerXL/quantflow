"""
Billing endpoints — plans, checkout, portal, webhook, subscription status.

POST /api/v1/billing/checkout      — start a subscription
POST /api/v1/billing/portal        — open Stripe Customer Portal
GET  /api/v1/billing/subscription  — current subscription status
POST /api/v1/billing/webhook       — Stripe webhook (no auth required)
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.response import success_response, error_http
from app.services.billing_service import (
    PRICE_IDS,
    PLAN_META,
    create_checkout_session,
    create_portal_session,
    get_subscription_status,
    handle_webhook,
)

router = APIRouter()

FRONTEND_URL = "https://quantflow.pages.dev"


@router.get("/subscription")
async def subscription(
    current_user: User = Depends(get_current_user),
):
    """Return the current user's subscription status and plan info."""
    # Read plan directly from database (webhook keeps it in sync)
    import stripe as stripe_mod

    plan_value = current_user.plan.value if hasattr(current_user.plan, "value") else str(current_user.plan)
    plan = PLAN_META.get(plan_value, PLAN_META["free"])

    sub_status = None
    period_end = None
    cancel_at_end = False
    amount = None
    interval = None

    # Try to get live subscription details from Stripe (best-effort)
    if current_user.stripe_subscription_id:
        try:
            sub = stripe_mod.Subscription.retrieve(current_user.stripe_subscription_id)
            sub_dict = sub.to_dict()
            sub_status = sub_dict.get("status")
            period_end = sub_dict.get("current_period_end")
            cancel_at_end = sub_dict.get("cancel_at_period_end", False)
            try:
                amount = sub_dict["items"]["data"][0]["price"]["unit_amount"]
                interval = sub_dict["items"]["data"][0]["price"]["recurring"]["interval"]
            except (KeyError, IndexError):
                pass
        except Exception:
            pass

    return success_response(data={
        "plan": plan_value,
        "plan_name": plan["name"],
        "status": sub_status,
        "current_period_end": str(period_end) if period_end else None,
        "cancel_at_period_end": cancel_at_end,
        "amount": amount,
        "interval": interval,
        "limits": plan["limits"],
        "prices": plan.get("prices"),
    })


@router.post("/checkout")
async def checkout(
    body: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a Stripe Checkout session for a subscription.

    Body:
        price_id: str — Stripe Price ID (e.g., price_pro_monthly)
        billing_period: "monthly" | "yearly" (optional, if price_id not given)

    Returns:
        {"checkout_url": "https://checkout.stripe.com/..."}
    """
    price_id = body.get("price_id")
    billing_period = body.get("billing_period", "monthly")
    plan = body.get("plan", "pro")

    # Resolve price_id from plan + period if not given directly
    if not price_id:
        plan_prices = PRICE_IDS.get(plan, {})
        price_id = plan_prices.get(billing_period, plan_prices.get("monthly", ""))

    if not price_id:
        raise error_http(
            "validation.error",
            "Invalid plan or billing period. Provide a valid price_id.",
            status_code=422,
        )

    success_url = f"{FRONTEND_URL}/dashboard/billing?checkout=success"
    cancel_url = f"{FRONTEND_URL}/dashboard/billing?checkout=cancelled"

    try:
        url = await create_checkout_session(
            user=current_user,
            db=db,
            price_id=price_id,
            success_url=success_url,
            cancel_url=cancel_url,
        )
        return success_response(data={"checkout_url": url})
    except RuntimeError as exc:
        raise error_http("external.api_error", str(exc), status_code=502)
    except Exception as exc:
        import logging, traceback
        logging.getLogger(__name__).error("Checkout failed: %s\n%s", exc, traceback.format_exc())
        raise error_http("server.error", f"Checkout error: {exc}", status_code=500)


@router.post("/portal")
async def portal(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a Stripe Customer Portal session.

    The portal lets users manage billing, update payment methods,
    and view invoices without leaving QuantFlow.

    Returns:
        {"portal_url": "https://billing.stripe.com/..."}
    """
    return_url = f"{FRONTEND_URL}/dashboard/billing"

    try:
        url = await create_portal_session(
            user=current_user,
            db=db,
            return_url=return_url,
        )
    except RuntimeError as exc:
        raise error_http("external.api_error", str(exc), status_code=502)

    return success_response(data={"portal_url": url})


@router.post("/webhook")
async def webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Stripe webhook endpoint.

    Receives events from Stripe: checkout completed, subscription
    updated/deleted, invoice payment failed.

    Requires the Stripe-Signature header for verification.
    No authentication required — uses Stripe webhook secret.
    """
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")

    result = await handle_webhook(payload, signature, db)
    if result.get("status") == "error":
        raise error_http(
            "external.api_error",
            result.get("message", "Webhook processing failed"),
            status_code=400,
        )
    return success_response(data=result)
