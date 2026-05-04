# tools.py — Conversational wrapper layer
#
# 💡 ROLE IN THE REFACTORED ARCHITECTURE:
#    This file is now a thin formatting layer that sits between the agent
#    loop and the two new layers beneath it:
#
#      tools_data.py  ← pure data operations (JSON read/write)
#      tools_ai.py    ← AI operations (calls Claude, returns structured dicts)
#           ↑
#      tools.py       ← YOU ARE HERE
#           ↑               converts structured dicts → conversational strings
#      agent.py       ← agent loop (calls run_tool, presents results to user)
#
#    This file does NOT contain business logic. Each function:
#      1. Calls tools_data or tools_ai
#      2. Formats the structured result as a readable string
#      3. Returns that string to the agent loop
#
#    Why keep this layer at all?
#      The Gradio UI and notebook still work via the agent loop, which expects
#      string responses. This layer preserves that contract while the new
#      data and AI layers return clean structured data for MCP.

from tools_data import (
    add_organisation,
    add_participant,
    add_participant_to_pipeline,
    get_all_organisations,
    get_all_participants,
    get_all_session_insights,
    get_organisation_by_id,
    get_panel_stats,
    get_participation_history,
    get_participant_by_id,
    get_project_by_id,
    get_project_data_for_summary,
    get_all_projects,
    create_project,
    import_participants_from_csv,
    record_session,
    save_session_summary,
    send_email_via_resend,
    update_participant,
)
from tools_ai import (
    draft_email_with_ai,
    extract_session_insights,
    screen_participants_with_ai,
    summarise_project_with_ai,
)


# ─────────────────────────────────────────────
# Tool descriptions (Claude reads these to decide which tool to call)
# ─────────────────────────────────────────────
#
# 💡 WHAT CHANGED vs. the original:
#    Tools that previously said "After calling this, you should..."
#    no longer need those instructions — the AI tools handle their
#    own reasoning internally now.

TOOLS = [
    {
        "name": "add_participant",
        "description": "Add a new participant to the research panel.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name":               {"type": "string"},
                "email":              {"type": "string"},
                "job_role":           {"type": "string"},
                "persona":            {"type": "string"},
                "seniority_level":    {"type": "string", "description": "Junior, Mid, Senior, Lead, or Executive"},
                "preferred_methods":  {"type": "array", "items": {"type": "string"}},
                "availability":       {"type": "string"},
                "organisation":       {"type": "string"},
                "notes":              {"type": "string"}
            },
            "required": ["name", "email", "job_role", "seniority_level", "preferred_methods", "availability"]
        }
    },
    {
        "name": "get_participant",
        "description": "Look up a participant by ID (e.g. P001) or name.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Participant ID or name"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "list_participants",
        "description": "List all participants, with optional filters by status, job role, or research method.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status":   {"type": "string"},
                "job_role": {"type": "string"},
                "method":   {"type": "string"}
            },
            "required": []
        }
    },
    {
        "name": "update_participant",
        "description": "Update one or more fields on a participant's profile. Only provide the fields you want to change.",
        "input_schema": {
            "type": "object",
            "properties": {
                "participant_id":    {"type": "string", "description": "ID or name of the participant"},
                "name":              {"type": "string"},
                "email":             {"type": "string"},
                "job_role":          {"type": "string"},
                "persona":           {"type": "string"},
                "organisation":      {"type": "string"},
                "organisation_id":   {"type": "string", "description": "Link to an org by ID, e.g. ORG-001"},
                "seniority_level":   {"type": "string"},
                "preferred_methods": {"type": "array", "items": {"type": "string"}},
                "availability":      {"type": "string"},
                "status":            {"type": "string", "description": "active, inactive, or do-not-contact"},
                "notes":             {"type": "string"}
            },
            "required": ["participant_id"]
        }
    },
    {
        "name": "create_project",
        "description": "Create a new research project with a name, goal, and screening criteria.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_name":        {"type": "string"},
                "research_goal":       {"type": "string"},
                "screening_criteria":  {
                    "type": "object",
                    "properties": {
                        "job_role":        {"type": "string"},
                        "seniority_level": {"type": "string"},
                        "methods":         {"type": "array", "items": {"type": "string"}},
                        "availability":    {"type": "string"},
                        "persona":         {"type": "string"}
                    }
                },
                "target_participants": {"type": "integer"},
                "notes":               {"type": "string"}
            },
            "required": ["project_name", "research_goal", "screening_criteria"]
        }
    },
    {
        "name": "get_project",
        "description": "Look up a project by ID (e.g. PRJ-001) or name. Returns full details including the participant pipeline.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Project ID or name"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "list_projects",
        "description": "List all research projects with status and progress at a glance.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "screen_participants",
        "description": (
            "Screen all active participants against a project's criteria using AI ranking. "
            "Returns participants ranked by fit score with reasoning. "
            "After presenting the results, offer to call add_to_pipeline for the participants "
            "the researcher wants to shortlist."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "e.g. PRJ-001"}
            },
            "required": ["project_id"]
        }
    },
    {
        "name": "add_to_pipeline",
        "description": "Add or update a participant in a project's pipeline with a status.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id":     {"type": "string"},
                "participant_id": {"type": "string"},
                "status":         {"type": "string", "description": "shortlisted, invited, confirmed, completed, or declined"}
            },
            "required": ["project_id", "participant_id", "status"]
        }
    },
    {
        "name": "draft_outreach_email",
        "description": (
            "Draft a personalised outreach email for a participant using AI. "
            "Returns a ready-to-review subject and body, personalised to their role and background. "
            "Present the draft to the researcher and wait for their approval before sending."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id":     {"type": "string"},
                "participant_id": {"type": "string"}
            },
            "required": ["project_id", "participant_id"]
        }
    },
    {
        "name": "send_outreach_email",
        "description": (
            "Send a finalised outreach email via Resend. "
            "Only call this after the researcher has reviewed and approved the draft."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "participant_id": {"type": "string"},
                "project_id":     {"type": "string"},
                "subject":        {"type": "string"},
                "body":           {"type": "string"}
            },
            "required": ["participant_id", "project_id", "subject", "body"]
        }
    },
    {
        "name": "record_session",
        "description": "Record a completed research session. Updates the participant's history and marks them as completed in the pipeline.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id":      {"type": "string"},
                "participant_id":  {"type": "string"},
                "touchpoint_type": {"type": "string", "description": "e.g. interview, usability test, survey"},
                "notes":           {"type": "string"}
            },
            "required": ["project_id", "participant_id", "touchpoint_type"]
        }
    },
    {
        "name": "get_participation_history",
        "description": "Show the full participation history for a participant — every project they've been involved in.",
        "input_schema": {
            "type": "object",
            "properties": {
                "participant_id": {"type": "string", "description": "ID or name"}
            },
            "required": ["participant_id"]
        }
    },
    {
        "name": "panel_overview",
        "description": "Show a high-level dashboard of the entire panel — totals, who hasn't been contacted, pipeline status across projects.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_project_summary",
        "description": (
            "Get an AI-generated project status summary — progress towards target, pipeline funnel, "
            "key observations from completed sessions, and a recommended next action."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string"}
            },
            "required": ["project_id"]
        }
    },
    {
        "name": "add_session_notes",
        "description": (
            "Save raw session notes and automatically extract structured insights using AI. "
            "Returns key insights, follow-up items, and notable quotes. "
            "No need to call save_session_summary separately — extraction is automatic."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "participant_id": {"type": "string", "description": "ID or name"},
                "project_id":     {"type": "string"},
                "raw_notes":      {"type": "string"}
            },
            "required": ["participant_id", "project_id", "raw_notes"]
        }
    },
    {
        "name": "save_session_summary",
        "description": "Manually save a structured session summary. Use add_session_notes instead if you have raw notes — it extracts insights automatically.",
        "input_schema": {
            "type": "object",
            "properties": {
                "participant_id":  {"type": "string"},
                "project_id":      {"type": "string"},
                "key_insights":    {"type": "array", "items": {"type": "string"}},
                "follow_up_items": {"type": "array", "items": {"type": "string"}},
                "quotes":          {"type": "array", "items": {"type": "string"}}
            },
            "required": ["participant_id", "project_id", "key_insights", "follow_up_items"]
        }
    },
    {
        "name": "get_participant_summary",
        "description": "Get all session insights for a participant across every project they've been involved in.",
        "input_schema": {
            "type": "object",
            "properties": {
                "participant_id": {"type": "string", "description": "ID or name"}
            },
            "required": ["participant_id"]
        }
    },
    {
        "name": "add_organisation",
        "description": "Add a new organisation to the directory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name":    {"type": "string"},
                "sector":  {"type": "string"},
                "size":    {"type": "string", "description": "startup, SME, scale-up, enterprise, micro-business, or sole trader"},
                "website": {"type": "string"},
                "notes":   {"type": "string"}
            },
            "required": ["name", "sector", "size"]
        }
    },
    {
        "name": "get_organisation",
        "description": "Look up an organisation by ID or name. Shows details and all linked participants.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "list_organisations",
        "description": "List all organisations in the directory with participant counts.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "import_participants_csv",
        "description": "Bulk-add participants from a CSV file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string"}
            },
            "required": ["file_path"]
        }
    },
]


# ─────────────────────────────────────────────
# Formatting wrappers
#
# 💡 Each function below:
#    1. Calls tools_data or tools_ai
#    2. Formats the structured result as a readable string
#    3. Returns that string to the agent loop
#
#    No logic lives here — just formatting.
# ─────────────────────────────────────────────

def _fmt_add_participant(**kwargs) -> str:
    result = add_participant(**kwargs)
    if not result["success"]:
        return f"❌ {result['error']}"
    p = result["participant"]
    return f"✅ Added {p['name']} to the panel (ID: {p['id']})."


def _fmt_get_participant(query: str) -> str:
    p = get_participant_by_id(query)
    if not p:
        return f"No participant found matching '{query}'."
    methods = ", ".join(p["preferred_methods"]) if p["preferred_methods"] else "not specified"
    sessions = len(p.get("participation_history", []))
    return (
        f"ID: {p['id']}\n"
        f"Name: {p['name']}\n"
        f"Email: {p['email']}\n"
        f"Role: {p['job_role']} ({p['seniority_level']})\n"
        f"Persona: {p.get('persona') or 'not set'}\n"
        f"Organisation: {p.get('organisation') or 'not set'}\n"
        f"Preferred methods: {methods}\n"
        f"Availability: {p['availability']}\n"
        f"Status: {p['status']}\n"
        f"Last touchpoint: {p['last_touchpoint'] or 'none'} {p['last_touchpoint_date']}\n"
        f"Sessions participated: {sessions}\n"
        f"Notes: {p.get('notes') or 'none'}\n"
        f"Date added: {p['date_added']}"
    )


def _fmt_list_participants(status: str = "", job_role: str = "", method: str = "") -> str:
    participants = get_all_participants(status=status, job_role=job_role, method=method)
    if not participants:
        return "No participants match those filters." if (status or job_role or method) \
               else "The panel is empty — no participants added yet."
    lines = [f"Found {len(participants)} participant(s):\n"]
    for p in participants:
        methods = ", ".join(p["preferred_methods"]) if p["preferred_methods"] else "none"
        lines.append(
            f"• {p['id']} — {p['name']} | {p['job_role']} ({p['seniority_level']}) | "
            f"Status: {p['status']} | Methods: {methods}"
        )
    return "\n".join(lines)


def _fmt_update_participant(participant_id: str, **kwargs) -> str:
    # Collect only the fields that were actually provided
    updates = {k: v for k, v in kwargs.items() if v is not None}
    result  = update_participant(participant_id, updates)
    if not result["success"]:
        return f"❌ {result['error']}"
    p = result["participant"]
    changes_text = "\n  ".join(result["changes"])
    return f"✅ Updated {p['name']} ({p['id']}):\n  {changes_text}"


def _fmt_create_project(
    project_name: str,
    research_goal: str,
    screening_criteria: dict,
    target_participants: int = 5,
    notes: str = ""
) -> str:
    result = create_project(
        project_name        = project_name,
        research_goal       = research_goal,
        screening_criteria  = screening_criteria,
        target_participants = target_participants,
        notes               = notes,
    )
    if not result["success"]:
        return f"❌ {result['error']}"
    proj = result["project"]
    return (
        f"✅ Created project '{proj['project_name']}' (ID: {proj['id']}).\n"
        f"Status: draft | Criteria: {screening_criteria}"
    )


def _fmt_get_project(query: str) -> str:
    proj = get_project_by_id(query)
    if not proj:
        return f"No project found matching '{query}'."

    sc = proj.get("screening_criteria", {})
    criteria_parts = []
    if sc.get("job_role"):        criteria_parts.append(f"Role: {sc['job_role']}")
    if sc.get("seniority_level"): criteria_parts.append(f"Seniority: {sc['seniority_level']}")
    if sc.get("methods"):         criteria_parts.append(f"Methods: {', '.join(sc['methods'])}")
    if sc.get("availability"):    criteria_parts.append(f"Availability: {sc['availability']}")
    criteria_text = " | ".join(criteria_parts) if criteria_parts else "none specified"

    pipeline = proj.get("pipeline_resolved", [])
    if pipeline:
        pipeline_lines = [
            f"  • {e['name']} ({e['participant_id']}) — {e['status']}"
            for e in pipeline
        ]
        pipeline_text = "\n".join(pipeline_lines)
    else:
        pipeline_text = "  No participants in pipeline yet."

    target    = proj.get("target_participants", "not set")
    completed = proj.get("completed_count", 0)
    progress  = f"{completed} of {target} completed" if isinstance(target, int) else "target not set"

    return (
        f"ID: {proj['id']}\n"
        f"Project: {proj['project_name']}\n"
        f"Goal: {proj['research_goal']}\n"
        f"Status: {proj['project_status']}\n"
        f"Progress: {progress}\n"
        f"Screening criteria: {criteria_text}\n"
        f"Participant pipeline:\n{pipeline_text}\n"
        f"Notes: {proj.get('notes') or 'none'}\n"
        f"Created: {proj['date_created']}"
    )


def _fmt_list_projects() -> str:
    projects = get_all_projects()
    if not projects:
        return "No projects yet. Create one with create_project!"
    lines = [f"Found {len(projects)} project(s):\n"]
    for proj in projects:
        target    = proj.get("target_participants", "?")
        completed = proj.get("completed_count", 0)
        active    = sum(
            1 for e in proj.get("participant_pipeline", [])
            if e.get("status") in {"shortlisted", "invited", "confirmed"}
        )
        lines.append(
            f"• {proj['id']} — {proj['project_name']} | "
            f"Status: {proj['project_status']} | "
            f"Progress: {completed}/{target} completed | "
            f"{active} in pipeline"
        )
    return "\n".join(lines)


def _fmt_screen_participants(project_id: str) -> str:
    result = screen_participants_with_ai(project_id)
    if not result["success"]:
        return f"❌ {result['error']}"

    ranked = result["ranked_participants"]
    if not ranked:
        return "No participants were returned by the screener."

    lines = [
        f"Screened {result['total_screened']} participants for "
        f"'{result['project_name']}' ({result['project_id']}).\n",
        "RANKED BY FIT:",
        "─" * 44,
    ]

    score_icon = lambda s: "🟢" if s >= 0.75 else ("🟡" if s >= 0.50 else "🔴")

    for p in ranked:
        score    = p.get("fit_score", 0)
        strengths = "; ".join(p.get("strengths", [])) or "none noted"
        concerns  = "; ".join(p.get("concerns",  [])) or "none"
        lines.append(
            f"\n{score_icon(score)} {p['name']} ({p['participant_id']}) — Fit: {score:.2f}\n"
            f"  {p.get('reasoning', '')}\n"
            f"  Strengths: {strengths}\n"
            f"  Concerns:  {concerns}"
        )

    lines.append("\n─" * 44)
    lines.append("Use add_to_pipeline to shortlist the participants you want to move forward with.")
    return "\n".join(lines)


def _fmt_add_to_pipeline(project_id: str, participant_id: str, status: str) -> str:
    result = add_participant_to_pipeline(project_id, participant_id, status)
    if not result["success"]:
        return f"❌ {result['error']}"
    action = result["action"].capitalize()
    return (
        f"{action} {result['participant_name']} ({participant_id}) → "
        f"{result['status']} in {result['project_name']}."
    )


def _fmt_draft_outreach_email(project_id: str, participant_id: str) -> str:
    result = draft_email_with_ai(participant_id, project_id)
    if not result["success"]:
        return f"❌ {result['error']}"
    personalisation = ", ".join(result.get("personalisation_used", [])) or "role and project goal"
    return (
        f"SUBJECT: {result['subject']}\n\n"
        f"{result['body']}\n\n"
        f"---\n"
        f"To: {result['recipient_name']} <{result['recipient_email']}>\n"
        f"Personalised with: {personalisation}"
    )


def _fmt_send_outreach_email(
    participant_id: str,
    project_id: str,
    subject: str,
    body: str
) -> str:
    result = send_email_via_resend(participant_id, project_id, subject, body)
    if not result["success"]:
        return f"❌ {result['error']}"
    return (
        f"✅ Email sent to {result['recipient_name']} ({result['recipient_email']}).\n"
        f"   Subject: {result['subject']}\n"
        f"   Pipeline status updated → invited."
    )


def _fmt_record_session(
    project_id: str,
    participant_id: str,
    touchpoint_type: str,
    notes: str = ""
) -> str:
    result = record_session(project_id, participant_id, touchpoint_type, notes)
    if not result["success"]:
        return f"❌ {result['error']}"
    p = result["participant"]
    return (
        f"✅ Recorded {touchpoint_type} session for {p['name']} "
        f"on {p['last_touchpoint_date']}.\n"
        f"They've now completed {result['total_sessions']} session(s) total."
    )


def _fmt_get_participation_history(participant_id: str) -> str:
    result = get_participation_history(participant_id)
    if not result["success"]:
        return f"❌ {result['error']}"
    p       = result["participant"]
    history = result["history"]
    if not history:
        return (
            f"{p['name']} ({p['id']}) has no recorded sessions yet.\n"
            f"Last touchpoint: {p['last_touchpoint'] or 'none'}"
        )
    lines = [
        f"Participation history for {p['name']} ({p['id']}):",
        f"Total sessions: {result['total']}",
        f"Last touchpoint: {p['last_touchpoint']} on {p['last_touchpoint_date']}",
        "─" * 40,
    ]
    for entry in history:
        note_text = f" — {entry['notes']}" if entry.get("notes") else ""
        lines.append(f"• {entry['date']} | {entry['project_name']} | {entry['method']}{note_text}")
    return "\n".join(lines)


def _fmt_panel_overview() -> str:
    stats = get_panel_stats()
    if stats["total"] == 0:
        return "The panel is empty — no participants added yet."

    lines = [
        "╔══════════════════════════════╗",
        "       PANEL OVERVIEW",
        "╚══════════════════════════════╝",
        "",
        f"👥 Total participants: {stats['total']}",
        f"   Active: {stats['active']} | Inactive: {stats['inactive']} | Do-not-contact: {stats['do_not_contact']}",
        "",
        f"📭 Never contacted: {len(stats['never_contacted'])}",
    ]
    for p in stats["never_contacted"]:
        lines.append(f"   • {p['name']} ({p['job_role']})")

    lines += ["", f"⏰ Not contacted in 60+ days: {len(stats['stale'])}"]
    for p in stats["stale"]:
        lines.append(f"   • {p['name']} — last: {p['last_touchpoint_date']}")

    lines += ["", "🏆 Most experienced participants:"]
    for p in stats["most_experienced"]:
        sessions = len(p["participation_history"])
        lines.append(f"   • {p['name']} — {sessions} session(s)")

    if stats["project_pipelines"]:
        lines += ["", "📋 Project pipelines:"]
        for proj in stats["project_pipelines"]:
            if proj["status_counts"]:
                counts_text = ", ".join(f"{v} {k}" for k, v in proj["status_counts"].items())
                lines.append(f"  • {proj['project_name']} ({proj['id']}): {counts_text}")

    return "\n".join(lines)


def _fmt_get_project_summary(project_id: str) -> str:
    result = summarise_project_with_ai(project_id)
    if not result["success"]:
        return f"❌ {result['error']}"

    d    = result["data"]
    pct  = (
        f"{int(d['completed_count'] / (d['completed_count'] + (d['still_needed'] or 0)) * 100)}%"
        if d.get("still_needed") is not None and (d["completed_count"] + d["still_needed"]) > 0
        else "n/a"
    )

    lines = [
        f"PROJECT SUMMARY — {result['project_name']} ({result['project_id']})",
        "═" * 50,
        "",
        result["status_summary"],
        "",
        "KEY OBSERVATIONS",
        "─" * 20,
    ]
    for obs in result.get("key_observations", []):
        lines.append(f"• {obs}")

    lines += [
        "",
        "RECOMMENDED NEXT ACTION",
        "─" * 20,
        result.get("recommended_next_action", ""),
        "",
        "─" * 50,
        f"Completed: {d['completed_count']} | "
        f"Still needed: {d['still_needed']} | "
        f"Shortlisted: {d['status_counts'].get('shortlisted', 0)} | "
        f"Invited: {d['status_counts'].get('invited', 0)}",
    ]
    return "\n".join(lines)


def _fmt_add_session_notes(participant_id: str, project_id: str, raw_notes: str) -> str:
    result = extract_session_insights(participant_id, project_id, raw_notes)
    if not result["success"]:
        return f"❌ {result['error']}"

    lines = [
        f"✅ Saved notes and extracted insights for "
        f"{result['participant_name']} ({result['project_name']}).",
        "",
        "KEY INSIGHTS",
        "─" * 30,
    ]
    for insight in result.get("key_insights", []):
        lines.append(f"• {insight}")

    if result.get("follow_up_items"):
        lines += ["", "FOLLOW-UP ITEMS", "─" * 30]
        for item in result["follow_up_items"]:
            lines.append(f"→ {item}")

    if result.get("quotes"):
        lines += ["", "NOTABLE QUOTES", "─" * 30]
        for quote in result["quotes"]:
            lines.append(f'"{quote}"')

    return "\n".join(lines)


def _fmt_save_session_summary(
    participant_id: str,
    project_id: str,
    key_insights: list,
    follow_up_items: list,
    quotes: list = None
) -> str:
    result = save_session_summary(participant_id, project_id, key_insights, follow_up_items, quotes)
    if not result["success"]:
        return f"❌ {result['error']}"
    c = result["insight_counts"]
    p = result["participant"]
    return (
        f"✅ Saved session summary for {p['name']}:\n"
        f"  {c['insights']} insight(s), {c['follow_ups']} follow-up(s), {c['quotes']} quote(s)."
    )


def _fmt_get_participant_summary(participant_id: str) -> str:
    result = get_all_session_insights(participant_id)
    if not result["success"]:
        return f"❌ {result['error']}"

    p        = result["participant"]
    insights = result["session_insights"]

    if not insights:
        return (
            f"{p['name']} has no session summaries yet. "
            f"Use add_session_notes after their first session."
        )

    lines = [
        f"SESSION SUMMARIES — {p['name']} ({p['id']})",
        f"Total sessions with notes: {len(insights)}",
        "═" * 44,
    ]
    for entry in insights:
        lines += [f"\n📋 {entry['project_name']} | {entry['date']}", "─" * 40]
        for insight in entry.get("key_insights", []):
            lines.append(f"  • {insight}")
        for item in entry.get("follow_up_items", []):
            lines.append(f"  → {item}")
        for quote in entry.get("quotes", []):
            lines.append(f'  "{quote}"')
    return "\n".join(lines)


def _fmt_add_organisation(
    name: str,
    sector: str,
    size: str,
    website: str = "",
    notes: str = ""
) -> str:
    result = add_organisation(name, sector, size, website, notes)
    if not result["success"]:
        return f"❌ {result['error']}"
    return f"✅ Added organisation '{result['org']['name']}' (ID: {result['org_id']})."


def _fmt_get_organisation(query: str) -> str:
    org = get_organisation_by_id(query)
    if not org:
        return f"No organisation found matching '{query}'."
    linked = org.get("linked_participants", [])
    lines  = [
        f"ID: {org['id']}",
        f"Name: {org['name']}",
        f"Sector: {org['sector']}",
        f"Size: {org['size']}",
        f"Website: {org.get('website') or 'not set'}",
        f"Notes: {org.get('notes') or 'none'}",
        f"Date added: {org['date_added']}",
        "",
        f"Linked participants ({len(linked)}):",
    ]
    if linked:
        for p in linked:
            lines.append(
                f"  • {p['name']} ({p['id']}) — {p['job_role']}, {p['seniority_level']} "
                f"| {p['sessions']} session(s) | Status: {p['status']}"
            )
    else:
        lines.append("  None linked yet — use update_participant with organisation_id to link people.")
    return "\n".join(lines)


def _fmt_list_organisations() -> str:
    orgs = get_all_organisations()
    if not orgs:
        return "No organisations added yet."
    lines = [f"Organisations ({len(orgs)} total):\n"]
    for org in orgs:
        lines.append(
            f"• {org['id']} — {org['name']} | {org['sector']} | {org['size']} "
            f"| {org['participant_count']} linked participant(s)"
        )
    return "\n".join(lines)


def _fmt_import_participants_csv(file_path: str) -> str:
    result = import_participants_from_csv(file_path)
    lines  = ["CSV import complete:"]
    if result.get("added"):
        lines.append(f"  ✅ Added {len(result['added'])}: {', '.join(result['added'])}")
    if result.get("skipped"):
        lines.append(f"  ⏭️  Skipped {len(result['skipped'])} (already in panel): {', '.join(result['skipped'])}")
    if result.get("errors"):
        lines.append(f"  ❌ {len(result['errors'])} error(s):")
        for e in result["errors"]:
            lines.append(f"     {e}")
    if not result.get("added") and not result.get("skipped") and not result.get("errors"):
        lines.append("  No rows found — is the file empty?")
    return "\n".join(lines)


# ─────────────────────────────────────────────
# Tool dispatcher — maps tool names → wrapper functions
# ─────────────────────────────────────────────

def run_tool(tool_name: str, tool_input: dict) -> str:
    """Looks up and runs a tool by name. Returns a conversational string."""

    tool_functions = {
        "add_participant":          _fmt_add_participant,
        "get_participant":          _fmt_get_participant,
        "list_participants":        _fmt_list_participants,
        "update_participant":       _fmt_update_participant,
        "create_project":           _fmt_create_project,
        "get_project":              _fmt_get_project,
        "list_projects":            _fmt_list_projects,
        "screen_participants":      _fmt_screen_participants,
        "add_to_pipeline":          _fmt_add_to_pipeline,
        "draft_outreach_email":     _fmt_draft_outreach_email,
        "send_outreach_email":      _fmt_send_outreach_email,
        "record_session":           _fmt_record_session,
        "get_participation_history":_fmt_get_participation_history,
        "panel_overview":           _fmt_panel_overview,
        "get_project_summary":      _fmt_get_project_summary,
        "add_session_notes":        _fmt_add_session_notes,
        "save_session_summary":     _fmt_save_session_summary,
        "get_participant_summary":  _fmt_get_participant_summary,
        "add_organisation":         _fmt_add_organisation,
        "get_organisation":         _fmt_get_organisation,
        "list_organisations":       _fmt_list_organisations,
        "import_participants_csv":  _fmt_import_participants_csv,
    }

    if tool_name not in tool_functions:
        return f"Error: tool '{tool_name}' not found."

    try:
        return tool_functions[tool_name](**tool_input)
    except Exception as e:
        return f"Error running '{tool_name}': {str(e)}"
