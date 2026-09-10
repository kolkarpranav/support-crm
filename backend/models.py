"""
backend/models.py

SQLAlchemy ORM models for the Support CRM database.

Tables
------
- tickets : stores every support ticket with AI triage metadata.
- notes   : internal notes attached to a ticket (human or AI-suggested).
"""

from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import relationship

from backend.database import Base


# ---------------------------------------------------------------------------
# Helper – returns current UTC time (timezone-aware).
# Used as column defaults so every timestamp is consistent.
# ---------------------------------------------------------------------------
def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  Ticket Model                                                           ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

class Ticket(Base):
    """Represents a customer-support ticket."""

    __tablename__ = "tickets"

    # --- Primary key ---
    id = Column(Integer, primary_key=True, autoincrement=True)

    # --- Human-friendly ticket identifier (e.g. TKT-001) ---
    ticket_id = Column(String, unique=True, index=True, nullable=False)

    # --- Customer information ---
    customer_name = Column(String, nullable=False)
    customer_email = Column(String, nullable=False)

    # --- Ticket content ---
    subject = Column(String, nullable=False)
    description = Column(Text, nullable=False)

    # --- Status & classification ---
    status = Column(String, default="Open")               # Open / In Progress / Closed
    priority = Column(String, default="Unassigned")        # Low / Medium / High / Critical
    category = Column(String, default="Uncategorized")     # Billing / Technical / Shipping / Account / General

    # --- AI triage fields ---
    ai_summary = Column(Text, nullable=True)               # AI-generated summary
    triage_status = Column(String, default="pending")       # pending / done

    # --- Timestamps ---
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    # --- Relationships ---
    notes = relationship("Note", back_populates="ticket", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return (
            f"<Ticket(ticket_id='{self.ticket_id}', "
            f"subject='{self.subject}', "
            f"status='{self.status}', "
            f"priority='{self.priority}')>"
        )


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  Note Model                                                             ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

class Note(Base):
    """An internal note attached to a ticket (human-written or AI-suggested)."""

    __tablename__ = "notes"

    # --- Primary key ---
    id = Column(Integer, primary_key=True, autoincrement=True)

    # --- Foreign key linking back to the parent ticket ---
    ticket_id = Column(
        String,
        ForeignKey("tickets.ticket_id"),
        nullable=False,
    )

    # --- Note content ---
    note_text = Column(Text, nullable=False)
    is_ai_suggested = Column(Boolean, default=False)

    # --- Timestamp ---
    created_at = Column(DateTime, default=_utcnow)

    # --- Relationships ---
    ticket = relationship("Ticket", back_populates="notes")

    def __repr__(self) -> str:
        return (
            f"<Note(id={self.id}, "
            f"ticket_id='{self.ticket_id}', "
            f"is_ai_suggested={self.is_ai_suggested})>"
        )
