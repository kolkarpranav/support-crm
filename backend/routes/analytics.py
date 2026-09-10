"""
backend/routes/analytics.py

Analytics endpoint that returns aggregated CRM metrics for the dashboard.

Endpoints
---------
GET /api/analytics – Return ticket counts, resolution time, and breakdowns.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Ticket
from backend.schemas import AnalyticsResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["analytics"])


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  GET /api/analytics                                                     ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

@router.get("/analytics", response_model=AnalyticsResponse)
def get_analytics(db: Session = Depends(get_db)):
    """Return aggregated dashboard metrics.

    Metrics include:
    - Total ticket count and breakdown by status.
    - Average resolution time (hours) for closed tickets.
    - Ticket counts grouped by priority and category.

    Parameters
    ----------
    db : Session
        SQLAlchemy database session (injected).

    Returns
    -------
    AnalyticsResponse
        All computed dashboard metrics. All counts default to 0 on an empty DB.
    """
    # --- Status counts ---
    total_tickets: int = db.query(func.count(Ticket.id)).scalar() or 0
    open_count: int = db.query(func.count(Ticket.id)).filter(Ticket.status == "Open").scalar() or 0
    in_progress_count: int = (
        db.query(func.count(Ticket.id)).filter(Ticket.status == "In Progress").scalar() or 0
    )
    closed_count: int = (
        db.query(func.count(Ticket.id)).filter(Ticket.status == "Closed").scalar() or 0
    )

    # --- Average resolution time (hours) for closed tickets only ---
    avg_resolution_hours: Optional[float] = None
    closed_tickets = db.query(Ticket).filter(Ticket.status == "Closed").all()
    if closed_tickets:
        total_hours = 0.0
        valid_count = 0
        for ticket in closed_tickets:
            if ticket.created_at and ticket.updated_at:
                delta = ticket.updated_at - ticket.created_at.replace(tzinfo=None) if ticket.created_at.tzinfo else ticket.updated_at - ticket.created_at
                hours = abs(delta.total_seconds()) / 3600
                total_hours += hours
                valid_count += 1
        if valid_count > 0:
            avg_resolution_hours = round(total_hours / valid_count, 2)

    # --- Priority breakdown ---
    priority_rows = (
        db.query(Ticket.priority, func.count(Ticket.id))
        .group_by(Ticket.priority)
        .all()
    )
    tickets_by_priority: dict[str, int] = {row[0]: row[1] for row in priority_rows if row[0]}

    # --- Category breakdown ---
    category_rows = (
        db.query(Ticket.category, func.count(Ticket.id))
        .group_by(Ticket.category)
        .all()
    )
    tickets_by_category: dict[str, int] = {row[0]: row[1] for row in category_rows if row[0]}

    return AnalyticsResponse(
        total_tickets=total_tickets,
        open_count=open_count,
        in_progress_count=in_progress_count,
        closed_count=closed_count,
        avg_resolution_hours=avg_resolution_hours,
        tickets_by_priority=tickets_by_priority,
        tickets_by_category=tickets_by_category,
    )
