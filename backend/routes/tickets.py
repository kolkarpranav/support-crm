"""
backend/routes/tickets.py

REST API routes for managing support tickets.

Endpoints
---------
POST   /api/tickets                          – Create a new ticket (AI triage runs in background)
GET    /api/tickets                          – List/search tickets with optional filters
GET    /api/tickets/{ticket_id}              – Retrieve full ticket detail with notes
PUT    /api/tickets/{ticket_id}              – Update ticket status and/or add a note
GET    /api/tickets/{ticket_id}/triage-status – Poll for AI triage completion
POST   /api/tickets/{ticket_id}/suggest-reply – Generate an AI reply suggestion
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Note, Ticket
from backend.schemas import TicketCreate, TicketListItem, TicketResponse, TicketUpdate
from backend.services.ai_service import suggest_reply, triage_ticket

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["tickets"])


# ---------------------------------------------------------------------------
# Background task: run AI triage and persist results
# ---------------------------------------------------------------------------

def _run_triage_and_update(ticket_id: str) -> None:
    """Execute AI triage for a ticket and write the results back to the database.

    This function is intended to be launched as a FastAPI BackgroundTask so
    that the HTTP response can be returned immediately while triage runs.

    Parameters
    ----------
    ticket_id : str
        The human-readable ticket identifier (e.g. ``TKT-001``).
    """
    # Import here to avoid a circular-import at module level
    from backend.database import SessionLocal

    db: Session = SessionLocal()
    try:
        ticket = db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
        if not ticket:
            logger.warning("Background triage: ticket %s not found.", ticket_id)
            return

        result = triage_ticket(ticket.subject, ticket.description)

        ticket.priority = result.get("priority", "Medium")
        ticket.category = result.get("category", "General")
        ticket.ai_summary = result.get("summary", "")
        ticket.triage_status = "done"
        ticket.updated_at = datetime.now(timezone.utc)

        db.commit()
        logger.info("Triage complete for %s – priority=%s", ticket_id, ticket.priority)

    except Exception as exc:
        logger.error("Background triage failed for %s: %s", ticket_id, exc)
        db.rollback()
    finally:
        db.close()


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  POST /api/tickets – Create ticket                                      ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

@router.post("/tickets", status_code=201)
def create_ticket(
    payload: TicketCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Create a new support ticket and kick off AI triage in the background.

    Parameters
    ----------
    payload : TicketCreate
        Validated request body containing customer details and ticket content.
    background_tasks : BackgroundTasks
        FastAPI background task queue.
    db : Session
        SQLAlchemy database session (injected).

    Returns
    -------
    dict
        Confirmation payload with the new ticket_id, created_at timestamp,
        and a status message.
    """
    # Generate a sequential, human-friendly ticket ID
    count = db.query(Ticket).count()
    ticket_id = f"TKT-{count + 1:03d}"

    new_ticket = Ticket(
        ticket_id=ticket_id,
        customer_name=payload.customer_name,
        customer_email=payload.customer_email,
        subject=payload.subject,
        description=payload.description,
        status="Open",
        priority="Unassigned",
        category="Uncategorized",
        triage_status="pending",
    )

    db.add(new_ticket)
    db.commit()
    db.refresh(new_ticket)

    # Fire-and-forget AI triage
    background_tasks.add_task(_run_triage_and_update, ticket_id)

    return {
        "ticket_id": ticket_id,
        "created_at": new_ticket.created_at,
        "message": "Ticket created. AI triage in progress.",
    }


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  GET /api/tickets – List / search tickets                               ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

@router.get("/tickets", response_model=list[TicketListItem])
def list_tickets(
    status: str | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
):
    """Return all tickets, optionally filtered by status and/or a search term.

    Parameters
    ----------
    status : str, optional
        Filter by ticket status (e.g. ``Open``, ``In Progress``, ``Closed``).
    search : str, optional
        Full-text search across customer_name, customer_email, subject,
        description, and ticket_id.
    db : Session
        SQLAlchemy database session (injected).

    Returns
    -------
    list[TicketListItem]
        Lightweight ticket summaries ordered newest-first.
    """
    query = db.query(Ticket)

    if status:
        query = query.filter(Ticket.status == status)

    if search:
        term = f"%{search}%"
        query = query.filter(
            Ticket.customer_name.ilike(term)
            | Ticket.customer_email.ilike(term)
            | Ticket.subject.ilike(term)
            | Ticket.description.ilike(term)
            | Ticket.ticket_id.ilike(term)
        )

    tickets = query.order_by(Ticket.created_at.desc()).all()
    return tickets


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  GET /api/tickets/{ticket_id} – Retrieve ticket detail                  ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

@router.get("/tickets/{ticket_id}", response_model=TicketResponse)
def get_ticket(ticket_id: str, db: Session = Depends(get_db)):
    """Return full detail for a single ticket including all notes.

    Parameters
    ----------
    ticket_id : str
        The human-readable ticket identifier (e.g. ``TKT-001``).
    db : Session
        SQLAlchemy database session (injected).

    Returns
    -------
    TicketResponse
        Full ticket data with embedded notes list.

    Raises
    ------
    HTTPException (404)
        If no ticket with the given ``ticket_id`` exists.
    """
    ticket = db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket '{ticket_id}' not found.")
    return ticket


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  PUT /api/tickets/{ticket_id} – Update status / add note               ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

@router.put("/tickets/{ticket_id}")
def update_ticket(
    ticket_id: str,
    payload: TicketUpdate,
    db: Session = Depends(get_db),
):
    """Update a ticket's status and/or append a new note.

    Parameters
    ----------
    ticket_id : str
        The human-readable ticket identifier.
    payload : TicketUpdate
        Fields to update. All fields are optional.
    db : Session
        SQLAlchemy database session (injected).

    Returns
    -------
    dict
        Success flag and the updated ``updated_at`` timestamp.

    Raises
    ------
    HTTPException (404)
        If no ticket with the given ``ticket_id`` exists.
    """
    ticket = db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket '{ticket_id}' not found.")

    if payload.status is not None:
        ticket.status = payload.status

    if payload.note_text:
        note = Note(
            ticket_id=ticket_id,
            note_text=payload.note_text,
            is_ai_suggested=payload.is_ai_suggested or False,
        )
        db.add(note)

    ticket.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(ticket)

    return {"success": True, "updated_at": ticket.updated_at}


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  GET /api/tickets/{ticket_id}/triage-status – Poll triage               ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

@router.get("/tickets/{ticket_id}/triage-status")
def get_triage_status(ticket_id: str, db: Session = Depends(get_db)):
    """Return the current AI triage status for a ticket.

    The frontend polls this endpoint every few seconds after ticket creation
    until ``triage_status`` equals ``"done"``.

    Parameters
    ----------
    ticket_id : str
        The human-readable ticket identifier.
    db : Session
        SQLAlchemy database session (injected).

    Returns
    -------
    dict
        ``ticket_id``, ``triage_status``, ``priority``, ``category``, and
        ``ai_summary``.

    Raises
    ------
    HTTPException (404)
        If no ticket with the given ``ticket_id`` exists.
    """
    ticket = db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket '{ticket_id}' not found.")

    return {
        "ticket_id": ticket.ticket_id,
        "triage_status": ticket.triage_status,
        "priority": ticket.priority,
        "category": ticket.category,
        "ai_summary": ticket.ai_summary,
    }


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  POST /api/tickets/{ticket_id}/suggest-reply – AI reply suggestion      ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

@router.post("/tickets/{ticket_id}/suggest-reply")
def get_reply_suggestion(ticket_id: str, db: Session = Depends(get_db)):
    """Generate an AI-powered reply suggestion for a support ticket.

    Parameters
    ----------
    ticket_id : str
        The human-readable ticket identifier.
    db : Session
        SQLAlchemy database session (injected).

    Returns
    -------
    dict
        ``suggested_reply`` string ready for the agent to send.

    Raises
    ------
    HTTPException (404)
        If no ticket with the given ``ticket_id`` exists.
    """
    ticket = db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket '{ticket_id}' not found.")

    # Build a readable notes history string
    notes_parts = []
    for note in ticket.notes:
        tag = "[AI]" if note.is_ai_suggested else "[Agent]"
        ts = note.created_at.strftime("%Y-%m-%d %H:%M") if note.created_at else ""
        notes_parts.append(f"{tag} {ts}: {note.note_text}")

    notes_history = "\n".join(notes_parts) if notes_parts else "No previous notes."

    reply = suggest_reply(
        ticket_subject=ticket.subject,
        ticket_description=ticket.description,
        customer_name=ticket.customer_name,
        notes_history=notes_history,
    )

    return {"suggested_reply": reply}
