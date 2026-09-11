# Support CRM — Customer Support Ticketing System

A full-stack customer support ticketing CRM with AI-powered triage, built as part of the Datastraw Technologies hiring assessment.

## Live Demo & Links
- 🌐 **Live App:** [support-crm-production-8a7b.up.railway.app](https://support-crm-production-8a7b.up.railway.app/app/index.html)
- 📁 **GitHub Repository:** [github.com/kolkarpranav/support-crm](https://github.com/kolkarpranav/support-crm)
- 🎥 **Demo Video:** [Watch Demo Video](https://your-video-link-here) *(Update with your video link)*
- 💼 **LinkedIn:** [My LinkedIn Profile](https://your-linkedin-link-here) *(Update with your LinkedIn profile)*

---

## Tech Stack

| Layer      | Technology                        |
|------------|-----------------------------------|
| Backend    | Python + FastAPI                  |
| Database   | Supabase (PostgreSQL)             |
| AI Engine  | Google Gemini 1.5 Flash           |
| Frontend   | HTML + Tailwind CSS + Vanilla JS  |
| Deployment | Railway                           |

---

## Why These Choices

- **FastAPI:** Built-in `BackgroundTasks` enabled non-blocking, asynchronous AI triage. Tickets save immediately while Gemini classifies in the background. Interactive docs at `/docs` simplified API development and testing.
- **Supabase (PostgreSQL):** SQLite stores data in ephemeral local files that get wiped on every Railway redeploy. Supabase keeps data in an external, persistent cloud PostgreSQL database.
- **Tailwind CSS & Vanilla JS:** Kept the frontend lightweight, dependency-free, and fast with zero bundle size while maintaining modern UI responsiveness.

---

## Features

### Core Features
- ✅ **Auto-Generated Ticket IDs:** Sequential, readable IDs (`TKT-001`, `TKT-002`, etc.).
- ✅ **Ticket Management:** View all tickets in a clean, filterable dashboard table.
- ✅ **Live Search & Filter:** 300ms debounced live search (name, email, subject, description) and status filter.
- ✅ **Detail & Notes View:** Comprehensive ticket view with full chronological discussion thread.
- ✅ **Status & Comment Updates:** Easily transition status (`Open`, `In Progress`, `Closed`) and save agent notes.

### AI-Powered Features
- 🤖 **Automated AI Triage:** Gemini 1.5 Flash automatically assigns priority (`Low`, `Medium`, `High`, `Critical`), categorizes issues (`Billing`, `Technical`, `Shipping`, `Account`, `General`), and generates a concise summary.
- 💡 **AI Reply Suggestions:** Generates context-aware, empathetic response drafts tailored to the conversation history.
- ⚡ **Non-Blocking Background Triage:** Instant ticket creation; triage runs via background task while the frontend polls until done.

### Analytics Dashboard
- 📊 Metrics for Total, Open, In Progress, and Closed tickets.
- ⏱️ Average resolution time for resolved tickets.
- 📈 Visual priority breakdown bars.
- 🗂️ Category distribution grid.

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | API health check |
| `POST` | `/api/tickets` | Create ticket & trigger background AI triage |
| `GET` | `/api/tickets` | List tickets with optional `?search=` and `?status=` |
| `GET` | `/api/tickets/{ticket_id}` | Get full ticket details with notes |
| `PUT` | `/api/tickets/{ticket_id}` | Update ticket status and/or append a note |
| `GET` | `/api/tickets/{ticket_id}/triage-status` | Poll AI triage status & classification |
| `POST` | `/api/tickets/{ticket_id}/suggest-reply` | Generate AI reply suggestion |
| `GET` | `/api/analytics` | Aggregated CRM performance metrics |

---

## Challenges Solved

- **1. Supabase IPv4 Pooler on Railway:** Railway environments connect using IPv6 by default, whereas Supabase pooler requires IPv4. Resolved by configuring Supabase's transaction pooler URL on port `6543` with `sslmode=require`.
- **2. Static Files & Router Mount Order:** In FastAPI, mounting `StaticFiles` first intercepts incoming API requests. Resolved by strictly structuring route registration: health check first, API routers second, and frontend static files last.
- **3. Asynchronous AI Latency:** Synchronous AI calls make ticket submission feel sluggish. Solved by leveraging FastAPI `BackgroundTasks` to respond instantly and run Gemini asynchronously while polling for completion.

---

## Local Setup

**1. Clone the repository**
```bash
git clone https://github.com/kolkarpranav/support-crm.git
cd support-crm
```

**2. Create and activate a virtual environment**
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Configure Environment Variables**
Create a `.env` file in the project root:
```env
DATABASE_URL=your_supabase_postgresql_connection_string
GEMINI_API_KEY=your_gemini_api_key
AI_MOCK_MODE=False
```

**5. Start the Application**
```bash
python -m uvicorn backend.main:app --reload --port 8000
```

**6. Access the App**
- **Dashboard:** [http://localhost:8000/app/index.html](http://localhost:8000/app/index.html)
- **Interactive API Docs (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)

---

## What I Would Add With More Time

- **Authentication & RBAC:** Multi-user authentication with role-based permissions (Admin, Agent, Viewer).
- **Email Notifications:** Automated webhooks or email alerts on ticket creation and status updates.
- **Agent Assignment:** Assigning tickets to specific agents or teams based on category and workload.
- **SLA Tracking:** SLA breach timers and visual priority escalations for overdue tickets.
- **Autonomous Agentic Loop:** Enabling the AI to query knowledge bases and suggest or trigger resolution workflows autonomously.
