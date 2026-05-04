# mcp_server.py
#
# 💡 ROLE IN THE ARCHITECTURE:
#    This is the MCP (Model Context Protocol) server. It exposes the
#    research panel's capabilities as tools that any MCP-compatible
#    client (Claude Desktop, other AI agents) can call directly.
#
#    It sits alongside — not replacing — the Gradio UI:
#
#      Gradio UI  →  agent.py  →  tools.py (formatting)  →  tools_data / tools_ai
#      Claude Desktop  →  mcp_server.py  →  tools_data / tools_ai  (direct, no formatting)
#
# 💡 WHY A SEPARATE SERVER?
#    The Gradio agent returns conversational strings ("Here are your results…").
#    An MCP client is code — it needs structured JSON, not prose.
#    This server calls tools_data and tools_ai directly and returns their
#    clean dicts, skipping the formatting layer entirely.
#
# 💡 HOW TO RUN:
#    uv run mcp_server.py
#    (uv handles Python 3.11 and dependencies automatically via pyproject.toml)
#
# 💡 HOW TO CONNECT TO CLAUDE DESKTOP:
#    See the bottom of this file, or SETUP.md, for the config snippet.

import os
import sys

# Make sure tools_data and tools_ai are importable when this file is run
# directly (e.g. uv run mcp_server.py from the project root)
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Import from our two layers (skipping tools.py — no formatting needed for MCP)
from tools_data import (
    add_participant,
    get_participant_by_id,
    get_participation_history,
)
from tools_ai import (
    draft_email_with_ai,
    extract_session_insights as _extract_session_insights,  # aliased to avoid name clash
    screen_participants_with_ai,
)

load_dotenv(os.path.join(os.path.dirname(__file__), ".env.local"), override=True)


# ─────────────────────────────────────────────
# Server
# ─────────────────────────────────────────────

mcp = FastMCP("Research Panel Manager")


# ─────────────────────────────────────────────
# Tool 1 — Screen participants
# ─────────────────────────────────────────────

@mcp.tool()
def screen_participants(project_id: str) -> dict:
    """
    Screen all active panel participants against a project's criteria using AI.

    Returns every candidate ranked by fit score (0.0–1.0), with a reasoning
    note, strengths, and concerns for each. Use this before recruiting to
    find the best-matched participants for a study.

    Args:
        project_id: The project ID to screen for, e.g. "PRJ-001".

    Returns a dict with:
        success (bool), project_id, project_name,
        ranked_participants (list of {participant_id, name, fit_score,
        reasoning, strengths, concerns}), total_screened.
    """
    return screen_participants_with_ai(project_id)


# ─────────────────────────────────────────────
# Tool 2 — Draft outreach email
# ─────────────────────────────────────────────

@mcp.tool()
def draft_outreach_email(participant_id: str, project_id: str) -> dict:
    """
    Draft a personalised recruitment email for a participant using AI.

    The email is written to match the participant's role, experience, and
    the project's research goal. It is NOT sent automatically — review the
    draft first, then send it via the Gradio UI or send_email tool.

    Args:
        participant_id: Participant ID (e.g. "P001") or full name.
        project_id:     Project ID (e.g. "PRJ-001").

    Returns a dict with:
        success (bool), subject (str), body (str),
        recipient_name, recipient_email, personalisation_used (list).
    """
    return draft_email_with_ai(participant_id, project_id)


# ─────────────────────────────────────────────
# Tool 3 — Extract session insights
# ─────────────────────────────────────────────

@mcp.tool()
def extract_session_insights(
    participant_id: str,
    project_id: str,
    raw_notes: str,
) -> dict:
    """
    Process messy raw session notes and extract structured research insights.

    Saves the raw notes, then uses AI to pull out key findings, follow-up
    actions, and notable participant quotes. Both the raw notes and the
    structured summary are stored against the participant's record.

    Args:
        participant_id: Participant ID (e.g. "P003") or full name.
        project_id:     Project ID (e.g. "PRJ-001").
        raw_notes:      Unstructured notes from the session — bullet points,
                        stream of consciousness, timestamps, all fine.

    Returns a dict with:
        success (bool), participant_name, project_name,
        key_insights (list), follow_up_items (list), quotes (list).
    """
    return _extract_session_insights(participant_id, project_id, raw_notes)


# ─────────────────────────────────────────────
# Tool 4 — Check participation history
# ─────────────────────────────────────────────

@mcp.tool()
def check_participation_history(participant_id: str) -> dict:
    """
    Get a participant's full history across every project they've been involved in.

    Use this before recruiting someone to avoid over-researching the same
    person, or to understand their prior contributions.

    Args:
        participant_id: Participant ID (e.g. "P001") or full name.

    Returns a dict with:
        success (bool), participant ({id, name, last_touchpoint,
        last_touchpoint_date}), history (list of {date, project_name,
        method, notes}), total (int).
    """
    return get_participation_history(participant_id)


# ─────────────────────────────────────────────
# Tool 5 — Add participant
# ─────────────────────────────────────────────

@mcp.tool()
def add_participant_to_panel(
    name: str,
    email: str,
    job_role: str,
    seniority_level: str,
    preferred_methods: list[str],
    availability: str,
    persona: str = "",
    organisation: str = "",
    notes: str = "",
) -> dict:
    """
    Add a new participant to the research panel.

    Args:
        name:               Full name, e.g. "Jane Smith".
        email:              Contact email.
        job_role:           Job title or function, e.g. "Product Manager".
        seniority_level:    One of: Junior, Mid, Senior, Lead, Executive.
        preferred_methods:  List of research methods they're open to,
                            e.g. ["interview", "usability test"].
        availability:       When they're generally free, e.g. "Weekday mornings".
        persona:            Optional persona tag, e.g. "Power User".
        organisation:       Optional company name.
        notes:              Any other relevant context.

    Returns a dict with:
        success (bool), participant_id (str), participant (full record), error (str).
    """
    return add_participant(
        name=name,
        email=email,
        job_role=job_role,
        seniority_level=seniority_level,
        preferred_methods=preferred_methods,
        availability=availability,
        persona=persona,
        organisation=organisation,
        notes=notes,
    )


# ─────────────────────────────────────────────
# Tool 6 — Get participant details
# ─────────────────────────────────────────────

@mcp.tool()
def get_participant_details(query: str) -> dict:
    """
    Look up a participant's full profile by ID or name.

    Args:
        query: Participant ID (e.g. "P001") or any part of their name.

    Returns a dict with:
        success (bool), participant (full profile including status,
        preferred_methods, availability, participation_history), error (str).
    """
    participant = get_participant_by_id(query)
    if participant is None:
        return {"success": False, "error": f"No participant found matching '{query}'"}
    return {"success": True, "participant": participant}


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────
#
# 💡 STDIO TRANSPORT:
#    Claude Desktop (and most MCP clients) talk to servers over stdin/stdout.
#    The server reads JSON-RPC messages from stdin, runs the right tool,
#    and writes the result back to stdout. No HTTP port needed.

if __name__ == "__main__":
    mcp.run(transport="stdio")


# ─────────────────────────────────────────────
# Claude Desktop configuration snippet
# ─────────────────────────────────────────────
#
# Add this to ~/Library/Application Support/Claude/claude_desktop_config.json:
#
# {
#   "mcpServers": {
#     "research-panel-manager": {
#       "command": "/Users/kaixisun/.local/bin/uv",
#       "args": [
#         "run",
#         "--python", "3.11",
#         "--with", "mcp",
#         "--with", "anthropic",
#         "--with", "python-dotenv",
#         "/Users/kaixisun/Desktop/GitHub/research-panel-manager/mcp_server.py"
#       ]
#     }
#   }
# }
#
# Then restart Claude Desktop. The six tools will appear in the tool panel.
