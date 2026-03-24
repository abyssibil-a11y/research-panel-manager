---
title: Research Panel Manager
emoji: 🧑‍🔬
colorFrom: violet
colorTo: purple
sdk: gradio
sdk_version: 4.20.0
app_file: app.py
pinned: false
---

# User Research Panel Manager

An AI-powered research ops tool that helps product teams manage participants, run intelligent screening, draft outreach emails, and capture session insights — all through a conversational interface.

Built with the Anthropic Claude API, Python, and Gradio. Designed as a portfolio project exploring how AI agents can accelerate product workflows.

---

## What it does

**Participant management**
Add, update, and organise research participants with rich profiles — demographics, expertise, preferred research methods, organisation, and participation history.

**Project tracking**
Create research projects with target criteria. The agent screens the panel, ranks candidates by fit, and manages a pipeline (shortlisted → invited → completed).

**Intelligent screening**
Claude reasons over the panel and explains *why* each participant is a good or poor fit for a given study — not just a yes/no match.

**Outreach email drafting**
Ask the agent to draft personalised outreach emails. If a participant has past session insights, those are automatically woven in to make the email more relevant.

**Session notes + insights**
Paste raw session notes and Claude extracts structured insights: key findings, quotes, follow-up items. Stored against the participant for future reference.

**Organisation tracking**
Link participants to organisations to track panel diversity and avoid over-recruiting from the same company.

**CSV import**
Bulk-import participants from a CSV file. A sample template is included.

**Email sending**
Send drafted emails directly via [Resend](https://resend.com) — with a human review step before anything is sent.

---

## Stack

| Layer | Tool | Why |
|---|---|---|
| AI reasoning | [Anthropic Claude API](https://anthropic.com) | Tool use + natural language reasoning |
| UI | [Gradio](https://gradio.app) | Python-native, fast to build, deployable to HF Spaces |
| Email | [Resend](https://resend.com) | Simple and free API |
| Data | JSON files | Human-readable, zero setup, right for this scale |
| Language | Python 3 | Consistent with the Anthropic SDK |

---

## Getting started

### 1. Clone the repo

```bash
git clone https://github.com/your-username/user-panel-manager.git
cd user-panel-manager
```

### 2. Install dependencies

```bash
pip install anthropic gradio==4.20.0 gradio_client==0.11.0 resend python-dotenv
```

### 3. Set up environment variables

Create a `.env.local` file in the root directory:

```
ANTHROPIC_API_KEY=your_key_here
RESEND_API_KEY=your_key_here
```

### 4. Run the app

```bash
python app.py
```

Or explore in the notebook:

```bash
jupyter notebook main.ipynb
```

---

## Project structure

```
user-panel-manager/
├── agent.py          # Agent loop + ChatSession class
├── tools.py          # All tools (data read/write + Claude-powered operations)
├── app.py            # Gradio UI
├── main.ipynb        # Step-by-step notebook walkthrough (Phases 1–8)
├── data/
│   ├── participants.json
│   ├── projects.json
│   └── organisations.json
└── sample_participants.csv
```

---

## Architecture

The project follows a clean separation between **data** and **intelligence**:

- **Tools** handle all reading and writing to JSON files. They are predictable, testable, and have no AI logic in them.
- **Claude** handles all reasoning — screening participants, ranking by fit, drafting emails, extracting insights from notes.
- **The agent loop** in `agent.py` connects them: it passes the conversation and available tools to Claude, executes whichever tools Claude calls, and loops until Claude returns a final answer.

```
User message
    → Claude reasons + selects tool(s)
        → Tool executes (reads/writes data)
            → Result returned to Claude
                → Claude reasons again or returns final answer
```

Multi-turn conversation memory is handled by `ChatSession`, which maintains message history with an optional sliding window (`max_turns`) to control token usage.

---

## Key decisions and trade-offs

### 1. JSON files instead of a database
**Decision:** All data lives in flat JSON files.

**Why:** Zero setup, human-readable, no SQL knowledge required. You can open `participants.json` and immediately understand the data model.

**Trade-off:** Doesn't scale beyond a few hundred records. No concurrent writes. No querying at the database level — Claude loads the full file and reasons over it. For production: SQLite or PostgreSQL.

---

### 2. Tools handle data, Claude handles intelligence
**Decision:** Tools do all CRUD operations. Claude does all reasoning.

**Why:** Clean separation of concerns. Tools are deterministic and easy to debug. Claude's reasoning is applied only where it genuinely adds value — screening, ranking, drafting, summarising.

**Trade-off:** Every smart operation requires an API call (cost + latency). A rule-based screener would be faster and cheaper, but far less flexible or explainable.

---

### 3. Full conversation history, sliding window ready
**Decision:** `ChatSession` stores full message history by default. A `max_turns` parameter is available but not activated.

**Why:** For short research sessions, full history gives Claude the best context. The trim option is built in for when conversations grow long enough to hit token limits.

**Trade-off:** Full history = richer context, higher token cost per message. Sliding window = cheaper, but Claude may lose earlier context.

---

### 4. Gradio instead of a custom web app
**Decision:** Use Gradio with `gr.Blocks` for the UI.

**Why:** Python-native, no frontend knowledge required, deployable to Hugging Face Spaces in one command.

**Trade-off:** Limited visual customisation, no multi-user auth, not production-grade. The right tool for a research prototype or internal tool — not a customer-facing product.

---

### 5. Human-in-the-loop before sending emails
**Decision:** The agent drafts emails and shows them to the researcher first. Sending only happens after explicit approval.

**Why:** Trust and safety. An AI sending a poorly-worded message to a research participant could damage relationships. The draft-then-review pattern keeps the researcher in control.

**Trade-off:** Adds a manual step. Worth it for any action that affects real people externally.

---

### 6. Session insights stored inside the participant record
**Decision:** `session_insights` is a nested list inside each participant object.

**Why:** Everything about a participant — profile, history, insights — is in one place. No joins needed.

**Trade-off:** Insights are denormalised. They belong to both a participant and a project, but only live in one place. For production: a separate `insights` table with foreign keys to both.

---

### 7. Organisation linked by both ID and display name
**Decision:** Participants store both `organisation_id` (`"ORG-001"`) and `organisation` (`"Spotify"`).

**Why:** The display name is immediately readable without a lookup. The ID enables proper relational linking — e.g. "find all participants from this company."

**Trade-off:** Slight redundancy. If an org name changes, it needs updating in two places. Acceptable at this scale.

---

### 8. CSV import using the built-in `csv` module
**Decision:** Use Python's built-in `csv.DictReader`, not pandas.

**Why:** No extra dependency. The use case is simple: read rows, map columns, write to JSON. Also handles BOM characters from Excel exports and gracefully reports per-row errors.

**Trade-off:** Less powerful for messy or complex data transformations. Pandas would be the next step for more advanced import logic.

---

### 9. No Dovetail integration
**Decision:** Decided not to build a Dovetail API integration despite it being on the original roadmap.

**Why:** Pulling raw transcripts from Dovetail would mean large token payloads with low signal — the panel manager only needs summaries, not full documents. Dovetail is also better suited for managing research documents; the panel manager owns the people data. Dovetail's 30-day token expiry adds operational friction for a background sync.

**The principle:** Good system design includes knowing what *not* to connect. Clear boundaries between tools make both easier to maintain.

---

### 10. Pinned Gradio to 4.20.0
**Decision:** `gradio==4.20.0` and `gradio_client==0.11.0` are pinned in dependencies.

**Why:** During development, `gradio 4.44.1` paired with `gradio_client 1.3.0` had a compatibility bug that broke the UI with a `TypeError`. Pinning to a known-good version pair was the pragmatic fix.

**The lesson:** Dependencies can break each other silently. Pin versions explicitly and test upgrades intentionally.

---

## Sample data

The repo includes sample JSON files with fictional participants, projects, and organisations so you can explore the agent immediately without adding your own data.

A `sample_participants.csv` template is also included for testing the CSV import feature.

---

## About

Built by [Zel](https://github.com/abyssibil-a11y) — a product designer learning to build with AI. This project explores how AI agents can reduce the operational overhead of running a user research panel, so the product teams spend less time on coordination and more time on real user insights, which is hugely overlooked by the current AI product development landscape.
