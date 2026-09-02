"""
Resend email service.

Resend free tier: 100 emails/day, 1 domain.
Used for transactional emails: welcome, upgrade reminders, payment failures.
"""

from __future__ import annotations

import html
import logging

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

SENDER = "QuantFlow <noreply@quantflow.io>"
FRONTEND_URL = "https://quantflow.io"


async def send_welcome_email(email: str, name: str) -> None:
    """Send a welcome email after registration."""
    # 2026-09-02 修复: name是用户可控输入, 未转义拼进HTML = 邮件内注入
    name = html.escape(name or "there", quote=True)
    html = f"""
    <div style="font-family: system-ui, sans-serif; max-width: 560px; margin: 0 auto;">
      <h1 style="color: #10b981;">Welcome to QuantFlow, {name}!</h1>
      <p style="color: #52525b; font-size: 16px; line-height: 1.6;">
        Your free account is ready to go. You get
        <strong style="color: #10b981;">5 free backtests per day</strong>.
      </p>
      <a href="{FRONTEND_URL}/backtest"
         style="display: inline-block; background: #10b981; color: #000;
                font-weight: 600; padding: 14px 28px; border-radius: 8px;
                text-decoration: none; margin-top: 16px;">
        Run Your First Backtest &rarr;
      </a>
      <hr style="border: none; border-top: 1px solid #e4e4e7; margin: 32px 0 16px;" />
      <p style="color: #a1a1aa; font-size: 13px;">
        Questions? Reply to this email — we read every one.
      </p>
    </div>
    """
    await _send(email, "Welcome to QuantFlow!", html)


async def send_upgrade_reminder(email: str) -> None:
    """Notify user they've reached their free daily limit."""
    html = f"""
    <div style="font-family: system-ui, sans-serif; max-width: 560px; margin: 0 auto;">
      <h2 style="color: #18181b;">Daily limit reached</h2>
      <p style="color: #52525b; font-size: 16px; line-height: 1.6;">
        You've used all 5 of your free backtests today.
        Upgrade to Pro for <strong>unlimited backtests</strong>.
      </p>
      <a href="{FRONTEND_URL}/dashboard/billing"
         style="display: inline-block; background: #10b981; color: #000;
                font-weight: 600; padding: 14px 28px; border-radius: 8px;
                text-decoration: none; margin-top: 16px;">
        Upgrade to Pro — $19/mo
      </a>
      <p style="color: #a1a1aa; font-size: 13px; margin-top: 24px;">
        Your limit resets tomorrow at midnight UTC.
      </p>
    </div>
    """
    await _send(email, "You've used all your free backtests today", html)


async def send_payment_failed_email(email: str) -> None:
    """Notify user of a failed subscription payment."""
    html = f"""
    <div style="font-family: system-ui, sans-serif; max-width: 560px; margin: 0 auto;">
      <h2 style="color: #dc2626;">Payment Failed</h2>
      <p style="color: #52525b; font-size: 16px; line-height: 1.6;">
        We couldn't process your latest subscription payment.
        Please update your payment method to avoid service interruption.
      </p>
      <a href="{FRONTEND_URL}/dashboard/billing"
         style="display: inline-block; background: #18181b; color: #fff;
                font-weight: 600; padding: 14px 28px; border-radius: 8px;
                text-decoration: none; margin-top: 16px;">
        Manage Billing &rarr;
      </a>
    </div>
    """
    await _send(email, "Payment failed — update your billing info", html)


async def send_reset_email(email: str, name: str, reset_url: str) -> None:
    """Send a password reset email."""
    # 2026-09-02 修复: 用户可控name转义(邮件内HTML注入)
    name_display = html.escape(name or "there", quote=True)
    html = f"""
    <div style="font-family: system-ui, sans-serif; max-width: 480px; margin: 0 auto;">
      <h2 style="color: #18181b;">Reset your password</h2>
      <p style="color: #52525b; font-size: 16px; line-height: 1.6;">
        Hi {name_display},
      </p>
      <p style="color: #52525b; font-size: 16px; line-height: 1.6;">
        Click the button below to reset your password.
        This link expires in <strong>10 minutes</strong>.
      </p>
      <a href="{reset_url}"
         style="display: inline-block; background: #10b981; color: #000;
                font-weight: 600; padding: 14px 28px; border-radius: 8px;
                text-decoration: none; margin: 16px 0;">
        Reset Password
      </a>
      <p style="color: #a1a1aa; font-size: 13px; margin-top: 24px;">
        If you didn't request this, you can safely ignore this email.<br/>
        This link will expire in 10 minutes and can only be used once.
      </p>
    </div>
    """
    await _send(email, "Reset your QuantFlow password", html)


async def _send(to: str, subject: str, html: str) -> None:
    """Low-level email sender via Resend API."""
    api_key = settings.RESEND_API_KEY
    if not api_key:
        logger.debug("Resend API key not configured — skipping email to %s", to)
        return

    try:
        import resend

        resend.api_key = api_key
        resend.Emails.send({
            "from": SENDER,
            "to": to,
            "subject": subject,
            "html": html,
        })
        logger.info("Email sent to %s: %s", to, subject)
    except Exception as exc:
        logger.warning("Failed to send email to %s: %s", to, exc)
