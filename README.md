---
title: Research Panel Manager
emoji: 🧑‍🔬
colorFrom: purple
colorTo: indigo
sdk: gradio
sdk_version: 5.25.0
app_file: app.py
pinned: false
---

# User Research Panel Manager

An AI-powered research ops tool that helps product teams manage participants, run intelligent screening, draft outreach emails, and capture session insights — all through a conversational interface.

Built with the Anthropic Claude API, Python, and Gradio. Designed as a portfolio project exploring how AI agents can accelerate product workflows.

**Two ways to use it:**
- **Chat UI** — run `python3 app.py` for a conversational Gradio interface
- **MCP server** — connect it to Claude Desktop or any MCP-compatible agent and call the tools directly

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

## Why this matters

Product researchers spend **3–5 hours per study** manually:
- Screening HubSpot/Airtable for qualified participants
- Drafting personalized outreach emails
- Tracking who's participated recently (to avoid over-recruiting)
- Extracting insights from messy session notes

This tool automates the tedious parts while keeping researchers in control of the human parts (deciding who to contact, approving messages before sending).

**Time saved per study: ~3 hours**  
**Quality improvement: Better participant matching, more personalized outreach**

---

## Stack

| Layer | Tool | Why |
|---|---|---|
| AI reasoning | [Anthropic Claude API](https://anthropic.com) | Tool use + forced structured output |
| Chat UI | [Gradio](https://gradio.app) | Python-native, fast to build, deployable to HF Spaces |
| MCP server | [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) | Expose tools to Claude Desktop and other AI agents |
| Runtime | [uv](https://github.com/astral-sh/uv) | Manages Python 3.11 for the MCP server without touching the system Python |
| Email | [Resend](https://resend.com) | Simple and free API |
| Data | JSON files | Human-readable, zero setup, right for this scale |
| Language | Python 3.9 (UI) / 3.11 (MCP) | 3.11 required by MCP SDK |

---

## Using in chat UI

### 1. Clone the repo

```bash
git clone https://github.com/abyssibil-a11y/research-panel-manager.git
cd research-panel-manager
```

### 2. Install dependencies

```bash
pip install anthropic gradio resend python-dotenv
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

### 5. Try it out

Once running:
1. **Add a participant** (use the "Participants" tab or import `sample_participants.csv`)
2. **Create a project** with target criteria (e.g., "Need 5 PMs for mobile usability study")
3. **Ask the agent** in the chat: "Screen the panel for this project and show me the top matches"
4. **Review** the agent's reasoning and draft outreach emails

The agent will explain *why* each participant is a good or poor fit, not just return a list.

---

## Using as an MCP server

Connect the panel manager directly to Claude Desktop so you can call its tools from any conversation — no chat UI needed.

### 1. Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

uv manages Python 3.11 and the MCP dependencies without touching your system Python.

### 2. Configure Claude Desktop

Open `~/Library/Application Support/Claude/claude_desktop_config.json` and add the `mcpServers` block (adjust the paths to match your machine):

```json
{
  "mcpServers": {
    "research-panel-manager": {
      "command": "/Users/YOUR_USERNAME/.local/bin/uv",
      "args": [
        "run",
        "--python", "3.11",
        "--with", "mcp",
        "--with", "anthropic",
        "--with", "python-dotenv",
        "/absolute/path/to/research-panel-manager/mcp_server.py"
      ]
    }
  }
}
```

A ready-to-edit template is in `mcp_config_example.json`.

### 3. Restart Claude Desktop

The six tools will be available in any new conversation.

### Available MCP tools

| Tool | Description | Key parameters |
|---|---|---|
| `screen_participants` | AI ranks all active panel members by fit | `project_id` |
| `draft_outreach_email` | AI writes a personalised recruitment email | `participant_id`, `project_id` |
| `extract_session_insights` | Processes raw notes → structured insights | `participant_id`, `project_id`, `raw_notes` |
| `check_participation_history` | Returns a participant's full project history | `participant_id` |
| `add_participant_to_panel` | Adds a new participant to the panel | `name`, `email`, `job_role`, `seniority_level`, `preferred_methods`, `availability` |
| `get_participant_details` | Looks up a participant by ID or name | `query` |

All tools return structured JSON with a `success` boolean and an `error` string on failure.

### Test the server

```bash
uv run test_mcp_tools.py
```

Runs 32 checks across all 6 tools and cleans up any test data it creates.

---

## Project structure

```
research-panel-manager/
├── agent.py               # Agent loop + ChatSession (used by Gradio UI)
├── tools.py               # Conversational formatting layer (Gradio UI only)
├── tools_data.py          # Pure data layer — all JSON read/write, no AI
├── tools_ai.py            # AI layer — structured Claude calls, forced tool use
├── mcp_server.py          # MCP server — exposes 6 tools to Claude Desktop
├── app.py                 # Gradio chat UI
├── pyproject.toml         # uv dependencies for the MCP server (Python 3.11)
├── mcp_config_example.json  # Copy-paste config for Claude Desktop
├── test_mcp_tools.py      # Integration tests for all 6 MCP tools
├── main.ipynb             # Step-by-step notebook walkthrough
├── data/
│   ├── participants.json
│   ├── projects.json
│   └── organisations.json
└── sample_participants.csv
```

---

## Architecture

The project uses a three-layer architecture with two client surfaces:

```
┌─────────────────────────────────────────────────────┐
│  Clients                                             │
│  ┌──────────────────┐    ┌────────────────────────┐ │
│  │  Gradio chat UI  │    │  Claude Desktop / MCP  │ │
│  │  (app.py)        │    │  (mcp_server.py)        │ │
│  └────────┬─────────┘    └───────────┬────────────┘ │
└───────────┼──────────────────────────┼──────────────┘
            │                          │
            ▼                          │
   agent.py + tools.py                 │
   (conversational strings)            │
            │                          │
            └──────────┬───────────────┘
                       ▼
          ┌────────────────────────┐
          │  tools_ai.py           │  ← AI operations
          │  (forced tool use,     │     (screen, draft,
          │   structured output)   │      insights, summary)
          └────────────┬───────────┘
                       │
          ┌────────────▼───────────┐
          │  tools_data.py         │  ← Pure data layer
          │  (JSON read/write,     │     (participants,
          │   no AI logic)         │      projects, orgs)
          └────────────────────────┘
```

**Key design principle:** `tools_data.py` and `tools_ai.py` return clean structured dicts — no prose, no formatting. The Gradio path (via `tools.py`) wraps those into conversational strings. The MCP path uses the structured dicts directly.

Multi-turn conversation memory is handled by `ChatSession` in `agent.py`, which maintains message history with an optional sliding window (`max_turns`) to control token usage.

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
**Decision:** Participants store both `organisation_id` (`"ORG-001"`) and `organisation` (`"Citylight Media"`).

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

### 10. MCP server runs on Python 3.11, Gradio UI runs on Python 3.9

**Decision:** The MCP server (`mcp_server.py`) uses Python 3.11 via `uv`. The Gradio UI (`app.py`) runs on the system Python 3.9. They are separate processes.

**Why:** The MCP Python SDK requires Python 3.10+. Rather than force-upgrading the whole project (and breaking existing Gradio compatibility), `uv` manages a separate Python 3.11 environment just for the MCP server. The data files they share are plain JSON — no compatibility issues.

**The lesson:** Polyglot runtime environments are normal. `uv` makes this painless — no virtualenv juggling, no system Python conflicts.

### 11. Forced tool use for guaranteed structured output

**Decision:** The AI layer (`tools_ai.py`) uses `tool_choice={"type": "tool", "name": "submit_result"}` to force Claude to return a specific JSON schema, rather than asking it to "reply in JSON".

**Why:** When you ask Claude to "reply in JSON", it might wrap the response in prose, vary the schema, or return markdown fences. Forced tool use is more reliable: Claude is trained to fill tool schemas accurately, so the output is consistent and parseable every time.

**The lesson:** The right abstraction for "I need structured data from an LLM" is tool use with a locked schema — not prompt engineering around JSON formatting.

---

## Sample data

The repo includes sample JSON files with fictional participants, projects, and organisations so you can explore the agent immediately without adding your own data.

A `sample_participants.csv` template is also included for testing the CSV import feature.

---

## What I learned building this

**Agent reasoning is powerful but unpredictable**  
The screening tool works beautifully when criteria are clear ("PMs with 5+ years experience"). It struggles when criteria are vague ("someone innovative"). The lesson: agents need structured inputs, not open-ended requests.

**Human-in-the-loop is essential for actions with external impact**  
Drafting an email is safe to automate. *Sending* an email requires human approval. This pattern (AI drafts, human approves) is the right model for operational AI.

**JSON files are the right choice at this scale**  
For 10–100 participants, JSON is simple and readable. The moment you need search/filtering/concurrency, migrate to SQLite. Know when to graduate to the next tier.

**Tool use is the core of agent capability**  
The agent doesn't "know" anything about participants. It calls tools that read the data, reasons over results, and calls more tools. The more reliable your tools, the more reliable your agent.

---

## About

Built by [Zel](https://github.com/abyssibil-a11y) — a product designer learning to build with AI. This project explores how AI agents can reduce the operational overhead of running a user research panel, so the product teams spend less time on coordination and more time on real user insights, which is hugely overlooked by the current AI product development landscape.
