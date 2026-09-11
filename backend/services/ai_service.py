"""
backend/services/ai_service.py

AI-powered features for the Support CRM using Google Gemini 1.5 Flash.

Functions
---------
- triage_ticket : Classify a ticket's priority, category, and generate a summary.
- suggest_reply  : Generate a professional reply for a customer support agent.

Both functions check ``settings.ai_mock_mode``:
- True  → return realistic mock data without calling the Gemini API.
- False → call the real Gemini API.
"""

import json
import re
import logging

import google.generativeai as genai

from backend.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Gemini model initialisation (happens once at import time)
# ---------------------------------------------------------------------------
genai.configure(api_key=settings.gemini_api_key)
model = genai.GenerativeModel("gemini-1.5-flash")


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  Triage Ticket                                                          ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

def triage_ticket(subject: str, description: str) -> dict:
    """Classify a support ticket using AI and return priority, category, and summary.

    Parameters
    ----------
    subject : str
        The ticket subject line.
    description : str
        The full ticket description from the customer.

    Returns
    -------
    dict
        A dictionary with keys: ``priority``, ``category``, ``summary``.
        Falls back to safe defaults on any error.
    """
    if settings.ai_mock_mode:
        return _mock_triage(subject, description)

    prompt = f"""You are an AI assistant for a customer support team.
Analyze this support ticket and respond ONLY with a JSON object.

Ticket Subject: {subject}
Ticket Description: {description}

Respond with ONLY this JSON, no other text:
{{
  "priority": "Low|Medium|High|Critical",
  "category": "Billing|Technical|Shipping|Account|General",
  "summary": "One sentence summary of the issue"
}}

Priority rules:
- Critical: account hacked, security breach, unauthorized access, data loss, system down, payment fraud, account compromised
- High: cannot login, cannot access account, order stuck, major feature broken, double charged, refund not received, payment failing
- Medium: partial feature issue, slow performance, billing question, wrong item received, app slow, tracking issue
- Low: general inquiry, feature request, minor issue, how to questions, address update, gift options

Category rules:
- Account: login, password, account hacked, unauthorized, profile
- Billing: payment, refund, charges, invoice, double charge
- Technical: app crash, bug, error, not working, crashing
- Shipping: delivery, tracking, lost package, wrong item, not arrived
- General: everything else"""

    try:
        response = model.generate_content(prompt)
        raw_text = response.text.strip()

        # Strip markdown code fences if present
        raw_text = re.sub(r"^```(?:json)?", "", raw_text, flags=re.MULTILINE).strip()
        raw_text = re.sub(r"```$", "", raw_text, flags=re.MULTILINE).strip()

        result = json.loads(raw_text)

        # Validate expected keys are present
        priority = result.get("priority", "Medium")
        category = result.get("category", "General")
        summary = result.get("summary", "Unable to auto-classify")

        # Sanitise values to allowed options
        valid_priorities = {"Low", "Medium", "High", "Critical"}
        valid_categories = {"Billing", "Technical", "Shipping", "Account", "General"}

        if priority not in valid_priorities:
            priority = "Medium"
        if category not in valid_categories:
            category = "General"

        return {"priority": priority, "category": category, "summary": summary}

    except Exception as exc:
        logger.error("Gemini triage_ticket failed: %s", exc)
        return {
            "priority": "Medium",
            "category": "General",
            "summary": "Unable to auto-classify",
        }


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  Suggest Reply                                                          ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

def suggest_reply(
    ticket_subject: str,
    ticket_description: str,
    customer_name: str,
    notes_history: str,
) -> str:
    """Generate a professional, empathetic reply for the support agent to send.

    Parameters
    ----------
    ticket_subject : str
        The subject of the ticket.
    ticket_description : str
        The customer's original description.
    customer_name : str
        The customer's name (used for personalisation).
    notes_history : str
        A pre-formatted string of all previous notes on the ticket.

    Returns
    -------
    str
        A ready-to-send reply message. Falls back to a generic message on error.
    """
    if settings.ai_mock_mode:
        return _mock_reply(ticket_subject, customer_name)

    prompt = f"""You are a helpful customer support agent.
Write a professional, empathetic reply to this customer.

Customer Name: {customer_name}
Issue Subject: {ticket_subject}
Issue Description: {ticket_description}
Previous Notes: {notes_history}

Write a reply that:
- Addresses the customer by name
- Acknowledges their issue specifically
- Provides helpful next steps
- Is professional but warm in tone
- Is 3-4 sentences maximum

Reply only with the message text, no subject line or signature."""

    try:
        response = model.generate_content(prompt)
        return response.text.strip()

    except Exception as exc:
        logger.error("Gemini suggest_reply failed: %s", exc)
        return (
            "Thank you for contacting support. "
            "We have received your ticket and will respond shortly."
        )


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  Mock Helpers (used when ai_mock_mode = True)                           ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

def _mock_triage(subject: str, description: str) -> dict:
    """Return realistic mock triage results based on keyword analysis.

    Parameters
    ----------
    subject : str
        The ticket subject.
    description : str
        The ticket description.

    Returns
    -------
    dict
        Mock priority, category, and summary.
    """
    combined = (subject + " " + description).lower()

    # --- Determine priority via keyword matching ---
    if any(kw in combined for kw in ["down", "outage", "data loss", "breach", "payment fail", "charge", "unauthorized"]):
        priority = "Critical"
    elif any(kw in combined for kw in ["cannot access", "locked out", "not working", "stuck", "broken", "error", "crash"]):
        priority = "High"
    elif any(kw in combined for kw in ["slow", "billing", "invoice", "partial", "question", "incorrect"]):
        priority = "Medium"
    else:
        priority = "Low"

    # --- Determine category via keyword matching ---
    if any(kw in combined for kw in ["bill", "invoice", "charge", "payment", "refund", "subscription"]):
        category = "Billing"
    elif any(kw in combined for kw in ["ship", "delivery", "order", "package", "tracking", "arrived"]):
        category = "Shipping"
    elif any(kw in combined for kw in ["account", "login", "password", "access", "locked", "profile"]):
        category = "Account"
    elif any(kw in combined for kw in ["bug", "error", "crash", "not working", "feature", "slow", "technical"]):
        category = "Technical"
    else:
        category = "General"

    summary = (
        f"Customer reported an issue related to {category.lower()} "
        f"with {priority.lower()} priority: {subject[:80]}"
    )

    return {"priority": priority, "category": category, "summary": summary}


def _mock_reply(ticket_subject: str, customer_name: str) -> str:
    """Return a generic but realistic mock reply.

    Parameters
    ----------
    ticket_subject : str
        The ticket subject, used to personalise the reply slightly.
    customer_name : str
        The customer's first name.

    Returns
    -------
    str
        A mock reply string.
    """
    first_name = customer_name.split()[0] if customer_name else "there"
    return (
        f"Hi {first_name}, thank you for reaching out to us regarding \"{ticket_subject}\". "
        f"I completely understand how frustrating this must be, and I want to assure you "
        f"that we are treating this as a priority. "
        f"Our team is actively looking into your case and we will provide you with a full "
        f"update within 24 hours — please don't hesitate to reply if you have any additional details to share."
    )
