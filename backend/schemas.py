"""
backend/schemas.py

Pydantic v2 schemas for request validation and response serialisation.

Naming convention
-----------------
- *Create  → incoming POST body
- *Update  → incoming PATCH/PUT body
- *Response → outgoing JSON response
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  Ticket Schemas                                                         ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

class TicketCreate(BaseModel):
    """Payload for creating a new ticket (POST /tickets)."""

    customer_name: str
    customer_email: EmailStr       # validates email format automatically
    subject: str
    description: str


class TicketUpdate(BaseModel):
    """Payload for updating an existing ticket (PATCH /tickets/{ticket_id}).

    All fields are optional – only the supplied fields are updated.
    """

    status: Optional[str] = None
    note_text: Optional[str] = None
    is_ai_suggested: Optional[bool] = None


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  Note Schemas                                                           ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

class NoteResponse(BaseModel):
    """Serialises a single note for API responses."""

    id: int
    ticket_id: str
    note_text: str
    is_ai_suggested: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  Ticket Response Schemas                                                ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

class TicketResponse(BaseModel):
    """Full ticket detail including all notes (GET /tickets/{ticket_id})."""

    id: int
    ticket_id: str
    customer_name: str
    customer_email: str
    subject: str
    description: str
    status: str
    priority: str
    category: str
    ai_summary: Optional[str] = None
    triage_status: str
    created_at: datetime
    updated_at: datetime
    notes: list[NoteResponse] = []

    model_config = ConfigDict(from_attributes=True)


class TicketListItem(BaseModel):
    """Lightweight ticket summary for list views (GET /tickets)."""

    ticket_id: str
    customer_name: str
    subject: str
    status: str
    priority: str
    category: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  Analytics Schema                                                       ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

class AnalyticsResponse(BaseModel):
    """Aggregated dashboard metrics (GET /analytics)."""

    total_tickets: int
    open_count: int
    in_progress_count: int
    closed_count: int
    avg_resolution_hours: Optional[float] = None
    tickets_by_priority: dict[str, int]
    tickets_by_category: dict[str, int]
