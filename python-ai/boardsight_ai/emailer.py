from __future__ import annotations

import json
import os
from typing import Any
from urllib import error, request


def resend_api_key() -> str:
    return (os.getenv("BOARDSIGHT_RESEND_API_KEY") or os.getenv("RESEND_API_KEY") or "").strip()


def email_from_address() -> str:
    return (os.getenv("BOARDSIGHT_EMAIL_FROM") or "").strip()


def email_reply_to() -> str:
    return (os.getenv("BOARDSIGHT_EMAIL_REPLY_TO") or "").strip()


def email_user_agent() -> str:
    return (os.getenv("BOARDSIGHT_EMAIL_USER_AGENT") or "boardsight-ai/1.0").strip()


def _send_resend_email(payload: dict[str, Any]) -> dict[str, Any]:
    api_key = resend_api_key()
    sender = email_from_address()
    if not api_key or not sender:
        return {
            "sent": False,
            "reason": "email_provider_not_configured",
        }

    payload = {"from": sender, **payload}
    reply_to = email_reply_to()
    if reply_to:
        payload["reply_to"] = reply_to

    encoded_payload = json.dumps(payload).encode("utf-8")
    http_request = request.Request(
        "https://api.resend.com/emails",
        data=encoded_payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": email_user_agent(),
        },
        method="POST",
    )
    try:
        with request.urlopen(http_request, timeout=10) as response:
            response_body = response.read().decode("utf-8") or "{}"
        parsed = json.loads(response_body)
        return {
            "sent": True,
            "provider": "resend",
            "provider_id": parsed.get("id"),
        }
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        return {
            "sent": False,
            "reason": f"resend_http_{exc.code}",
            "detail": detail[:500],
        }
    except Exception as exc:  # pragma: no cover - network/provider dependent
        return {
            "sent": False,
            "reason": "resend_request_failed",
            "detail": str(exc),
        }


def send_verification_email(*, to_email: str, display_name: str, verification_url: str) -> dict[str, Any]:
    return _send_resend_email(
        {
            "to": [to_email],
            "subject": "Verify your BoardSight account",
            "html": (
                f"<p>Hi {display_name or 'there'},</p>"
                "<p>Thanks for registering for BoardSight.</p>"
                f"<p><a href=\"{verification_url}\">Verify your email</a></p>"
                "<p>If you did not create this account, you can ignore this email.</p>"
            ),
        }
    )


def send_billing_reminder_email(
    *,
    to_email: str,
    display_name: str,
    workspace_name: str,
    plan_name: str,
    billing_cycle: str,
    renewal_date_label: str,
    manage_url: str,
    days_offset: int,
    grace_period_days: int,
) -> dict[str, Any]:
    if days_offset > 1:
        subject = f"BoardSight renewal due in {days_offset} days"
        intro = f"Your {workspace_name} workspace renews in {days_offset} days."
    elif days_offset == 1:
        subject = "BoardSight renewal due tomorrow"
        intro = f"Your {workspace_name} workspace renews tomorrow."
    elif days_offset == 0:
        subject = "BoardSight renewal due today"
        intro = f"Your {workspace_name} workspace renews today."
    else:
        elapsed = abs(days_offset)
        subject = f"BoardSight renewal overdue by {elapsed} days"
        intro = (
            f"Your {workspace_name} workspace renewal is overdue by {elapsed} days. "
            f"You still have a {grace_period_days}-day grace window before paid access is paused."
        )
    return _send_resend_email(
        {
            "to": [to_email],
            "subject": subject,
            "html": (
                f"<p>Hi {display_name or 'there'},</p>"
                f"<p>{intro}</p>"
                f"<p><strong>Plan:</strong> {plan_name} ({billing_cycle})<br>"
                f"<strong>Renewal date:</strong> {renewal_date_label}</p>"
                f"<p><a href=\"{manage_url}\">Open BoardSight billing</a></p>"
                "<p>Renewing manually keeps the workspace active without needing autopay.</p>"
            ),
        }
    )
