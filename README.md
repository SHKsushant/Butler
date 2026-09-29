# The Butler — Inbox-to-Action Butler

Turns a messy inbox / support-ticket export into a triaged, prioritized,
draft-reply-ready queue, with a human approving every reply before it
counts as "sent." Built for the *Build Fast with AI: AI Build Challenge
2026* — Track 06.

## What it does

1. **Ingest** a CSV/JSON export of support tickets/emails.
2. **Classify** each one (category, urgency 1-5, sentiment, confidence)
   with Llama 3.1 8B via Groq's free API. Low-confidence classifications
   are auto-flagged for human double-checking instead of trusted silently.
3. **Embed & cluster** tickets with a deterministic local similarity model so duplicate
   reports of the same issue (e.g. 5 people reporting one outage) are
   grouped instead of shown as 5 separate rows.
4. **Prioritize** with a transparent, auditable weighted formula — not
   another opaque LLM call — combining urgency, sentiment, VIP status,
   cluster size, and **SLA risk** (how close each ticket is to its
   category's response-time deadline).
5. **Draft a reply** per ticket with Llama 3.3 70B via Groq's free API,
   grounded in a small FAQ knowledge base via lightweight retrieval (RAG).
6. **Human review dashboard**: every draft is approved, edited, or
   rejected by a person before anything counts as sent — individually,
   or in bulk for a whole duplicate cluster at once. Nothing is actually
   emailed — this satisfies the "human in the loop" requirement without
   needing real mail-sending infrastructure.
7. **Insights panel & CSV export**: a live analytics view (category/
   sentiment breakdown, SLA breaches, review flags) and a downloadable
   audit trail of every decision made.

## Project structure

```
backend/
  app/
    main.py               FastAPI app + all endpoints
    models.py              SQLAlchemy model + Pydantic schemas
    database.py             SQLite setup
    services/
      ingestion.py           CSV/JSON parsing
      classification.py       category/urgency/sentiment/confidence via Llama 3.1 8B (Groq)
      embeddings.py           Sentence-Transformers wrapper
      dedup.py                cosine-similarity clustering
      prioritization.py       explainable weighted priority score (incl. SLA risk)
      sla.py                  per-category SLA targets + breach/risk computation
      faq_retrieval.py        small RAG lookup over the FAQ set
      draft_generator.py       action type + reply draft via Llama 3.3 70B (Groq)
      llm_client.py           thin Groq API wrapper w/ JSON mode, parsing + retry
    data/
      faq.py                 hardcoded FAQ knowledge base (stand-in for real docs)
  tests/                    pytest suite for SLA, prioritization, dedup, ingestion
  Dockerfile
  requirements.txt
  requirements-dev.txt      adds pytest for running the test suite
  .env.example
frontend/
  index.html              single-file dashboard (no build step) — queue, filters,
                            insights panel, keyboard shortcuts
  Dockerfile
sample_data/
  tickets_sample.csv       10 sample tickets, including intentional near-duplicates
                            for the dedup/clustering feature to demonstrate on
docker-compose.yml        runs backend + frontend together with one command
```

## Setup

### Option A: Docker (fastest way to run the whole thing)

```bash
cp backend/.env.example backend/.env
# edit backend/.env and paste your free Groq API key
# docker compose reads backend/.env automatically
docker compose up --build
```

Backend: `http://localhost:8000` · Frontend: `http://localhost:5500`

### Option B: Run locally

**Backend:**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# PowerShell: Copy-Item .env.example .env
cp .env.example .env
# edit .env and paste your free Groq API key (get one at console.groq.com/keys —
# no credit card required)

# .env is loaded automatically on local startup
uvicorn app.main:app --reload --port 8000
```

The app runs without a model download. For stronger semantic duplicate
matching, install `pip install -r requirements-ml.txt`, then set
`USE_SEMANTIC_EMBEDDINGS=true`; the first run downloads `all-MiniLM-L6-v2`.

Check it's alive: open `http://localhost:8000/docs` for interactive
Swagger docs of every endpoint.

**Frontend:** `frontend/index.html` is a single static file — no build
step. Just open it in a browser, or serve it with any static server:

```bash
cd frontend
python3 -m http.server 5500
```

Then open `http://localhost:5500`. The dashboard has an "API" field in
the toolbar (defaults to `http://localhost:8000`) — point it at wherever
your backend is running or deployed.

### Running the tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest tests/ -v
```

24 tests cover the SLA logic, the prioritization formula, dedup
clustering, and CSV/JSON ingestion — all pure logic, no API key or
network access needed to run them.

### Try it end-to-end

1. Open the dashboard.
2. Upload `sample_data/tickets_sample.csv` (it has intentional
   near-duplicate tickets to demonstrate clustering, and realistic
   timestamps to demonstrate SLA breach on first run).
3. Click **Run triage pipeline** — watch the step-by-step progress
   animation as it classifies, embeds, clusters, prioritizes, and
   drafts replies for every new ticket.
4. Try the **filters** (category, VIP, needs-review, SLA-at-risk) and
   the search box, or use keyboard shortcuts: `j`/`k` to navigate,
   `a`/`r` to approve/reject, `/` to search.
5. Click a ticket to see its full detail, priority reasoning, SLA
   status, and drafted reply. Edit the draft if you want, then
   **Approve & send** or **Reject** — or, for a duplicate cluster,
   **approve the reply for all similar tickets at once**.
6. Open **Insights** for the analytics panel, or **Export decisions**
   for a CSV audit trail.

## Deployment for submission

### Vercel (single public URL)

This repository is configured for a single Vercel deployment: it serves the
dashboard and FastAPI endpoints from the same URL. Import the GitHub repository
with the **Root Directory** set to `inbox-butler` (or leave it at the repository
root when this folder is the repository root), then add `GROQ_API_KEY` in the
Vercel project environment variables. Do not upload `backend/.env`.

- **Framework Preset**: FastAPI
- **Build Command**: leave Vercel's detected default
- **Output Directory**: leave blank

Vercel functions use ephemeral storage, so ticket data may reset after a new
deployment or a cold start. This is suitable for the hackathon demo; use a
hosted Postgres database for persistent production data.

- **Backend**: Render or Railway both deploy a FastAPI app directly from
  a GitHub repo (or use the included `Dockerfile`). Set `GROQ_API_KEY`
  as an environment variable in the platform's dashboard — never commit it.
- **Frontend**: Vercel or Netlify can serve `frontend/index.html`
  directly as a static site. After deploying the backend, open the
  dashboard's API field and point it at the deployed backend URL, e.g.
  `https://your-backend.onrender.com`.
- Update this README with your actual deployed links before submission.

## Design choices worth mentioning in your PPT

- **Two-model strategy, both free via Groq**: Llama 3.1 8B for high-volume
  classification (fast), Llama 3.3 70B for the customer-facing draft
  (worth the extra capability since a human reads it).
- **Why Groq**: a genuinely free, no-credit-card developer tier — no
  billing setup needed for the team or for judges who want to run this
  themselves.
- **Prioritization is a plain, auditable formula, not another LLM call**
  — combines urgency, sentiment, VIP status, cluster size, and SLA risk,
  and every weight is a named constant you can defend on the spot.
- **The AI reports its own uncertainty**: classification confidence
  drives an automatic "needs human review" flag, instead of treating
  every AI output as equally trustworthy.
- **Grounded drafts**: a small FAQ retrieval step feeds real policy
  context into the reply prompt so the model doesn't invent details.
- **Every LLM call has a safe default** if the JSON response fails to
  parse, so one bad response never breaks the batch.
- **Human-in-the-loop by construction**: the `/tickets/{id}/decision`
  and `/tickets/cluster/{id}/resolve` endpoints are the only ways a
  ticket's status changes to approved/rejected — there is no code path
  that sends anything without a human decision.
- **Tested, not just demoed**: 24 automated tests cover the core logic,
  and the whole stack runs from one `docker compose up`.

## What to build out further if you have time left

- Real inbox/ticket-system integration (Gmail API, Zendesk, etc.)
  instead of a CSV export.
- Persisted audit log of who (which team member) approved what, not
  just when.
- Configurable SLA targets and priority weights from the dashboard
  instead of hardcoded constants.
