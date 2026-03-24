# tools.py — Phase 1 + 2 + 3 + 4: Participants, Projects, Screening, and Tracking
#
# 💡 PHASE 1 RECAP: JSON files as a simple database
#    We store participants as a list in participants.json.
#    Reading and writing that file is how we "save" and "load" data.
#
# 💡 PHASE 2 NEW CONCEPT: Linking data by ID
#    Projects live in a separate file (projects.json) and reference
#    participants by their ID — not by copying their full profile.
#
#    Example: a project's participant_pipeline looks like:
#    [
#      { "participant_id": "P001", "status": "shortlisted" },
#      { "participant_id": "P003", "status": "invited" }
#    ]
#
#    When we want to show names, we look them up from participants.json.
#    Store the data once → reference it everywhere. Same idea as VLOOKUP!

import json     # built-in Python tool for reading/writing JSON
import os       # built-in Python tool for file paths
from datetime import date   # built-in Python tool for today's date

# Path to our data files — os.path.join builds the path safely on any OS
BASE_DIR         = os.path.dirname(__file__)   # the folder this file lives in
PARTICIPANTS_FILE  = os.path.join(BASE_DIR, "data", "participants.json")
PROJECTS_FILE      = os.path.join(BASE_DIR, "data", "projects.json")
ORGANISATIONS_FILE = os.path.join(BASE_DIR, "data", "organisations.json")

# TOOLS
# ── Participants ─────────────────── add_participant, get_participant, list_participants, update_participant
# ── Projects ─────────────────────── create_project, get_project, screen_participants, add_to_pipeline
# ── Organisations ────────────────── add_organisation, get_organisation, list_organisations
# ── Outreach & Email ─────────────── draft_outreach_email, send_outreach_email
# ── Session Notes ────────────────── record_session, add_session_notes, save_session_summary
# ── Import ───────────────────────── import_participants_csv


# ─────────────────────────────────────────────
# Helper functions (not tools — just utilities)
# ─────────────────────────────────────────────

def _load_participants() -> list:
    """Reads participants.json and returns the list. Returns [] if file is empty."""
    with open(PARTICIPANTS_FILE, "r") as f:
        data = json.load(f)
    return data if data else []


def _save_participants(participants: list):
    """Writes the updated list back to participants.json."""
    with open(PARTICIPANTS_FILE, "w") as f:
        json.dump(participants, f, indent=2)   # indent=2 makes it human-readable


def _generate_id(participants: list) -> str:
    """
    Auto-generates the next participant ID.
    If there are 3 participants, the next one gets P004.
    💡 This is like auto-increment in a spreadsheet.
    """
    next_number = len(participants) + 1
    return f"P{next_number:03d}"   # :03d means "pad with zeros to 3 digits" → P001, P002...


def _load_projects() -> list:
    """Reads projects.json and returns the list."""
    with open(PROJECTS_FILE, "r") as f:
        data = json.load(f)
    return data if data else []


def _save_projects(projects: list):
    """Writes the updated list back to projects.json."""
    with open(PROJECTS_FILE, "w") as f:
        json.dump(projects, f, indent=2)


def _generate_project_id(projects: list) -> str:
    """Auto-generates the next project ID, e.g. PRJ-001, PRJ-002..."""
    next_number = len(projects) + 1
    return f"PRJ-{next_number:03d}"


def _load_organisations() -> list:
    """Reads organisations.json. Returns [] if empty."""
    with open(ORGANISATIONS_FILE, "r") as f:
        data = json.load(f)
    return data if data else []


def _save_organisations(organisations: list):
    """Writes the updated list back to organisations.json."""
    with open(ORGANISATIONS_FILE, "w") as f:
        json.dump(organisations, f, indent=2)


def _generate_org_id(organisations: list) -> str:
    """Auto-generates the next org ID, e.g. ORG-001, ORG-002..."""
    next_number = len(organisations) + 1
    return f"ORG-{next_number:03d}"


def _format_insights_for_email(participant: dict) -> str:
    """
    Formats a participant's past session insights for inclusion in email drafts.
    Returns an empty string if there are no insights yet — so existing emails
    still work exactly the same for participants without session history.
    """
    insights_list = participant.get("session_insights", [])
    all_follow_ups = []
    all_quotes     = []

    for entry in insights_list:
        all_follow_ups.extend(entry.get("follow_up_items", []))
        all_quotes.extend(entry.get("quotes", []))

    if not all_follow_ups and not all_quotes:
        return ""   # no insights yet — email drafting works as before

    lines = ["\nPAST SESSION CONTEXT (use to personalise the email):"]
    if all_follow_ups:
        lines.append("Follow-up items from previous sessions:")
        for item in all_follow_ups:
            lines.append(f"  → {item}")
    if all_quotes:
        lines.append("Things they said previously:")
        for quote in all_quotes:
            lines.append(f'  "{quote}"')
    lines.append("Reference these naturally — don't list them literally in the email.")

    return "\n".join(lines)


def _participant_name(participant_id: str, participants: list) -> str:
    """
    💡 THIS IS THE CROSS-REFERENCING MOMENT!
    Given a participant ID like 'P001', looks up their name
    from the participants list — same idea as VLOOKUP in a spreadsheet.
    """
    for p in participants:
        if p["id"] == participant_id:
            return p["name"]
    return f"Unknown ({participant_id})"   # fallback if ID not found


# ─────────────────────────────────────────────
# Tool descriptions (Claude reads these)
# ─────────────────────────────────────────────

TOOLS = [
    {
        "name": "add_participant",
        "description": "Add a new participant to the research panel. Use this when a researcher wants to add someone new to their panel.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name":               { "type": "string", "description": "Full name" },
                "email":              { "type": "string", "description": "Email address" },
                "job_role":           { "type": "string", "description": "Job title, e.g. 'Product Designer'" },
                "persona":            { "type": "string", "description": "Research persona label, e.g. 'Design Lead', 'Power User'" },
                "seniority_level":    { "type": "string", "description": "e.g. Junior, Mid, Senior, Lead, Executive" },
                "preferred_methods":  {
                    "type": "array",
                    "items": { "type": "string" },
                    "description": "List of preferred research methods, e.g. ['interview', 'usability test', 'survey']"
                },
                "availability":       { "type": "string", "description": "When they're free, e.g. 'weekday mornings'" },
                "organisation":       { "type": "string", "description": "Company name (optional)" },
                "notes":              { "type": "string", "description": "Any extra notes (optional)" }
            },
            "required": ["name", "email", "job_role", "seniority_level", "preferred_methods", "availability"]
        }
    },
    {
        "name": "get_participant",
        "description": "Look up a single participant by their ID (e.g. P001) or by name. Returns their full profile.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": { "type": "string", "description": "Participant ID (e.g. P001) or name to search for" }
            },
            "required": ["query"]
        }
    },
    {
        "name": "list_participants",
        "description": "List all participants in the panel. Can optionally filter by status, job role, or preferred research method.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status":   { "type": "string", "description": "Filter by status: active, inactive, or do-not-contact" },
                "job_role": { "type": "string", "description": "Filter by job role keyword, e.g. 'designer'" },
                "method":   { "type": "string", "description": "Filter by preferred method, e.g. 'interview'" }
            },
            "required": []
        }
    },
    {
        "name": "create_project",
        "description": "Create a new research project with a name, goal, and screening criteria. Use this when a researcher wants to set up a new study.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_name":  { "type": "string", "description": "Short name for the project, e.g. 'Checkout Flow Redesign'" },
                "research_goal": { "type": "string", "description": "What the researcher is trying to learn" },
                "screening_criteria": {
                    "type": "object",
                    "description": "Who they're looking for",
                    "properties": {
                        "job_role":        { "type": "string",  "description": "Target job role keyword, e.g. 'designer'" },
                        "seniority_level": { "type": "string",  "description": "e.g. Senior, Mid, any" },
                        "methods":         { "type": "array", "items": { "type": "string" }, "description": "Required research methods, e.g. ['interview']" },
                        "availability":    { "type": "string",  "description": "Required availability, e.g. 'weekday mornings'" }
                    }
                },
                "target_participants": { "type": "integer", "description": "How many participants the researcher wants to complete sessions for this project, e.g. 5" },
                "notes": { "type": "string", "description": "Any extra notes or context (optional)" }
            },
            "required": ["project_name", "research_goal", "screening_criteria"]
        }
    },
    {
        "name": "get_project",
        "description": "Look up a research project by ID (e.g. PRJ-001) or name. Returns full project details including the participant pipeline with names.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": { "type": "string", "description": "Project ID (e.g. PRJ-001) or project name to search for" }
            },
            "required": ["query"]
        }
    },
    {
        "name": "screen_participants",
        # 💡 This tool fetches the data. Claude does the reasoning.
        #    After calling this, Claude should call add_to_pipeline
        #    for each participant it decides is a good fit.
        "description": (
            "Fetch a project's screening criteria and all active participants so you can assess fit. "
            "After reviewing the results, call add_to_pipeline for each participant you decide to shortlist. "
            "Rank by how well they match the role, seniority, preferred methods, and availability."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": { "type": "string", "description": "The project ID to screen for, e.g. PRJ-001" }
            },
            "required": ["project_id"]
        }
    },
    {
        "name": "add_to_pipeline",
        "description": "Add or update a participant in a project's pipeline with a status (shortlisted, invited, confirmed, completed, declined).",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id":      { "type": "string", "description": "Project ID, e.g. PRJ-001" },
                "participant_id":  { "type": "string", "description": "Participant ID, e.g. P001" },
                "status":          { "type": "string", "description": "One of: shortlisted, invited, confirmed, completed, declined" }
            },
            "required": ["project_id", "participant_id", "status"]
        }
    },
    {
        "name": "draft_outreach_email",
        # 💡 Same pattern as screen_participants:
        #    The tool fetches the context, Claude writes the email.
        "description": (
            "Fetch a participant's profile and project details so you can draft a personalised outreach email. "
            "Write a warm, professional email inviting them to participate. "
            "Reference their specific role and the research goal to make it feel personal, not templated."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id":     { "type": "string", "description": "Project ID, e.g. PRJ-001" },
                "participant_id": { "type": "string", "description": "Participant ID, e.g. P001" }
            },
            "required": ["project_id", "participant_id"]
        }
    },
    {
        "name": "record_session",
        # 💡 PHASE 4 — the key action tool
        #    Updates TWO places at once:
        #      1. participant.participation_history (appends a new entry)
        #      2. project.participant_pipeline (marks status as "completed")
        "description": "Record that a research session has been completed with a participant. Updates their participation history and marks them as completed in the project pipeline.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id":      { "type": "string", "description": "Project ID, e.g. PRJ-001" },
                "participant_id":  { "type": "string", "description": "Participant ID, e.g. P001" },
                "touchpoint_type": { "type": "string", "description": "Type of session, e.g. interview, usability test, survey, diary study" },
                "notes":           { "type": "string", "description": "Optional notes about the session" }
            },
            "required": ["project_id", "participant_id", "touchpoint_type"]
        }
    },
    {
        "name": "get_participation_history",
        "description": "Show the full participation history for a participant — every project they've been involved in, with dates and session types.",
        "input_schema": {
            "type": "object",
            "properties": {
                "participant_id": { "type": "string", "description": "Participant ID, e.g. P001, or their name" }
            },
            "required": ["participant_id"]
        }
    },
    {
        "name": "panel_overview",
        "description": "Show a high-level dashboard of the entire research panel — total participants, session counts, who hasn't been contacted recently, and pipeline status across projects. Use this for questions like 'how's the panel looking?' or 'who should we reach out to next?'",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "list_projects",
        "description": "List all research projects with their status and progress at a glance. Use this when a researcher wants to see all projects or get a quick overview of what's running.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_project_summary",
        # 💡 Same pattern as panel_overview and screen_participants:
        #    the tool fetches and formats the data,
        #    Claude reads it and adds the intelligent layer —
        #    pattern observations, next recommended actions.
        "description": (
            "Get a detailed research ops summary for a project — progress towards target, "
            "pipeline funnel, who needs following up, and session insights collected so far. "
            "After reading the data, summarise the project status in plain language and "
            "suggest the single most important next action."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": { "type": "string", "description": "Project ID, e.g. PRJ-001" }
            },
            "required": ["project_id"]
        }
    },
    {
        "name": "add_session_notes",
        # 💡 Same pattern as screen_participants and draft_outreach_email:
        #    the tool saves the raw data, Claude does the intelligence.
        #    After calling this, Claude should call save_session_summary
        #    with its structured extraction of insights.
        "description": (
            "Save raw notes from a research session to a participant's profile. "
            "After saving, read the notes carefully and call save_session_summary "
            "to store your structured extraction of key insights, follow-up items, and notable quotes."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "participant_id": { "type": "string", "description": "Participant ID or name" },
                "project_id":     { "type": "string", "description": "Project ID, e.g. PRJ-001" },
                "raw_notes":      { "type": "string", "description": "The raw session notes to save" }
            },
            "required": ["participant_id", "project_id", "raw_notes"]
        }
    },
    {
        "name": "save_session_summary",
        "description": "Save your structured summary of a session after reading the raw notes. Call this after add_session_notes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "participant_id":  { "type": "string", "description": "Participant ID or name" },
                "project_id":      { "type": "string", "description": "Project ID, e.g. PRJ-001" },
                "key_insights":    {
                    "type": "array", "items": { "type": "string" },
                    "description": "2–4 key research insights from this session"
                },
                "follow_up_items": {
                    "type": "array", "items": { "type": "string" },
                    "description": "Specific things to follow up on in the next interaction with this participant"
                },
                "quotes": {
                    "type": "array", "items": { "type": "string" },
                    "description": "1–3 notable direct quotes worth preserving"
                }
            },
            "required": ["participant_id", "project_id", "key_insights", "follow_up_items"]
        }
    },
    {
        "name": "get_participant_summary",
        "description": "Get a full summary of a participant's research history — all session insights, follow-up items, and quotes across every project they've been involved in. Use this when you need deep context about a participant, especially before drafting outreach.",
        "input_schema": {
            "type": "object",
            "properties": {
                "participant_id": { "type": "string", "description": "Participant ID or name" }
            },
            "required": ["participant_id"]
        }
    },
    {
        "name": "send_outreach_email",
        # 💡 HUMAN-IN-THE-LOOP:
        #    This tool only gets called AFTER the researcher has seen the draft
        #    (from draft_outreach_email) and explicitly said "send it".
        #    The conversation history bridges the two calls —
        #    Claude remembers the draft and constructs the send call from it.
        "description": (
            "Send a finalised outreach email to a participant via Resend. "
            "Only call this after the researcher has reviewed and approved the draft. "
            "After sending, the participant's pipeline status is automatically updated to 'invited'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "participant_id": { "type": "string", "description": "Participant ID, e.g. P001" },
                "project_id":     { "type": "string", "description": "Project ID, e.g. PRJ-001" },
                "subject":        { "type": "string", "description": "Email subject line" },
                "body":           { "type": "string", "description": "Full plain-text email body" }
            },
            "required": ["participant_id", "project_id", "subject", "body"]
        }
    },
    {
        "name": "add_organisation",
        "description": "Add a new organisation to the directory. Use this when a researcher wants to register a company so participants can be properly linked to it.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name":    { "type": "string", "description": "Organisation name, e.g. 'Spotify'" },
                "sector":  { "type": "string", "description": "Industry sector, e.g. 'consumer tech', 'fintech', 'healthtech', 'enterprise software'" },
                "size":    { "type": "string", "description": "Company size: startup, SME, or enterprise" },
                "website": { "type": "string", "description": "Website URL (optional)" },
                "notes":   { "type": "string", "description": "Any extra context (optional)" }
            },
            "required": ["name", "sector", "size"]
        }
    },
    {
        "name": "get_organisation",
        "description": "Look up an organisation by ID or name. Shows its details and all linked participants.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": { "type": "string", "description": "Organisation ID (e.g. ORG-001) or name" }
            },
            "required": ["query"]
        }
    },
    {
        "name": "list_organisations",
        "description": "List all organisations in the directory, with participant counts.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "import_participants_csv",
        "description": "Import multiple participants at once from a CSV file. Use this when a researcher wants to bulk-add participants from a spreadsheet. The file should follow the sample template format.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": { "type": "string", "description": "Path to the CSV file, e.g. 'data/my_panel.csv' or an absolute path" }
            },
            "required": ["file_path"]
        }
    },
    {
        "name": "update_participant",
        "description": "Update one or more fields on an existing participant's profile. Use this when a researcher wants to change someone's details — e.g. they changed jobs, updated their availability, or should be marked inactive or do-not-contact. Only provide the fields you want to change.",
        "input_schema": {
            "type": "object",
            "properties": {
                "participant_id":    { "type": "string", "description": "ID or name of the participant to update, e.g. P001 or 'Sarah Chen'" },
                "name":              { "type": "string", "description": "Updated full name" },
                "email":             { "type": "string", "description": "Updated email address" },
                "job_role":          { "type": "string", "description": "Updated job title" },
                "persona":           { "type": "string", "description": "Updated persona label" },
                "organisation":      { "type": "string", "description": "Updated company name (free text)" },
                "organisation_id":   { "type": "string", "description": "Link to an organisation in the directory by ID, e.g. ORG-001. Also updates the organisation display name automatically." },
                "seniority_level":   { "type": "string", "description": "Updated seniority: Junior, Mid, Senior, Lead, Executive" },
                "preferred_methods": {
                    "type": "array",
                    "items": { "type": "string" },
                    "description": "Updated list of preferred research methods"
                },
                "availability":      { "type": "string", "description": "Updated availability, e.g. 'weekday afternoons'" },
                "status":            { "type": "string", "description": "Updated status: active, inactive, or do-not-contact" },
                "notes":             { "type": "string", "description": "Updated notes" }
            },
            "required": ["participant_id"]
        }
    }
]


# ─────────────────────────────────────────────
# Tool functions
# ─────────────────────────────────────────────

def add_participant(
    name: str,
    email: str,
    job_role: str,
    seniority_level: str,
    preferred_methods: list,
    availability: str,
    persona: str = "",
    organisation: str = "",
    notes: str = ""
) -> str:
    """
    Adds a new participant to participants.json.

    💡 HOW IT WORKS (step by step):
       1. Load the current list from the file
       2. Check the email isn't already in there
       3. Build a new participant object (like a JS object)
       4. Add it to the list
       5. Save the updated list back to the file
    """
    participants = _load_participants()

    # Prevent duplicate emails
    for p in participants:
        if p["email"].lower() == email.lower():
            return f"A participant with email '{email}' already exists (ID: {p['id']})."

    # Build the participant object
    # 💡 This is the schema we designed together!
    new_participant = {
        "id":                 _generate_id(participants),
        "name":               name,
        "email":              email,
        "job_role":           job_role,
        "persona":            persona,
        "organisation":       organisation,
        "seniority_level":    seniority_level,
        "preferred_methods":  preferred_methods,
        "availability":       availability,
        "status":             "active",          # everyone starts as active
        "last_touchpoint":    "",
        "last_touchpoint_date": "",
        "participation_history": [],             # empty list — no sessions yet
        "notes":              notes,
        "date_added":         str(date.today())  # auto-set to today
    }

    participants.append(new_participant)
    _save_participants(participants)

    return f"✅ Added {name} to the panel (ID: {new_participant['id']})."


def get_participant(query: str) -> str:
    """
    Finds a participant by ID or name and returns their full profile.

    💡 HOW IT WORKS:
       1. Load the list
       2. Look for a match by ID (exact) or name (fuzzy — contains the query)
       3. Return their profile as readable text
    """
    participants = _load_participants()

    if not participants:
        return "The panel is empty — no participants added yet."

    query_lower = query.lower()
    match = None

    for p in participants:
        # Match by ID (exact) or name (partial, case-insensitive)
        if p["id"].lower() == query_lower or query_lower in p["name"].lower():
            match = p
            break

    if not match:
        return f"No participant found matching '{query}'."

    # Format as readable text for Claude to summarise
    methods = ", ".join(match["preferred_methods"]) if match["preferred_methods"] else "not specified"
    history_count = len(match["participation_history"])

    return (
        f"ID: {match['id']}\n"
        f"Name: {match['name']}\n"
        f"Email: {match['email']}\n"
        f"Role: {match['job_role']} ({match['seniority_level']})\n"
        f"Persona: {match['persona'] or 'not set'}\n"
        f"Organisation: {match['organisation'] or 'not set'}\n"
        f"Preferred methods: {methods}\n"
        f"Availability: {match['availability']}\n"
        f"Status: {match['status']}\n"
        f"Last touchpoint: {match['last_touchpoint'] or 'none'} {match['last_touchpoint_date']}\n"
        f"Sessions participated: {history_count}\n"
        f"Notes: {match['notes'] or 'none'}\n"
        f"Date added: {match['date_added']}"
    )


def list_participants(status: str = "", job_role: str = "", method: str = "") -> str:
    """
    Lists all participants, with optional filters.

    💡 HOW IT WORKS:
       1. Load the list
       2. Filter based on whatever the researcher asked for
       3. Return a summary of each match
    """
    participants = _load_participants()

    if not participants:
        return "The panel is empty — no participants added yet."

    # Apply filters (only if the researcher specified them)
    filtered = participants

    if status:
        filtered = [p for p in filtered if p["status"].lower() == status.lower()]

    if job_role:
        filtered = [p for p in filtered if job_role.lower() in p["job_role"].lower()]

    if method:
        filtered = [p for p in filtered if any(method.lower() in m.lower() for m in p["preferred_methods"])]

    if not filtered:
        return "No participants match those filters."

    # Build a summary list
    lines = [f"Found {len(filtered)} participant(s):\n"]
    for p in filtered:
        methods = ", ".join(p["preferred_methods"]) if p["preferred_methods"] else "none"
        lines.append(
            f"• {p['id']} — {p['name']} | {p['job_role']} ({p['seniority_level']}) | "
            f"Status: {p['status']} | Methods: {methods}"
        )

    return "\n".join(lines)


def create_project(
    project_name: str,
    research_goal: str,
    screening_criteria: dict,
    target_participants: int = 5,
    notes: str = ""
) -> str:
    """
    Creates a new research project and saves it to projects.json.

    💡 HOW IT WORKS:
       1. Load existing projects
       2. Build a new project object — notice screening_criteria is a
          nested object (a dict inside a dict), just like in our schema design
       3. participant_pipeline starts empty — Phase 3 will populate it
       4. Save back to projects.json
    """
    projects = _load_projects()

    new_project = {
        "id":                   _generate_project_id(projects),
        "project_name":         project_name,
        "research_goal":        research_goal,
        "project_status":       "draft",      # always starts as draft
        "target_participants":  target_participants,
        "screening_criteria":   screening_criteria,
        "participant_pipeline": [],           # empty for now — Phase 3 fills this
        "notes":                notes,
        "date_created":         str(date.today())
    }

    projects.append(new_project)
    _save_projects(projects)

    return (
        f"✅ Created project '{project_name}' (ID: {new_project['id']}).\n"
        f"Status: draft | Looking for: {screening_criteria}"
    )


def get_project(query: str) -> str:
    """
    Finds a project by ID or name and returns its full details.

    💡 THE CROSS-REFERENCING MOMENT:
       The participant_pipeline stores IDs like 'P001'.
       To show human-readable names, we load participants.json
       and look up each ID — exactly like VLOOKUP.

       projects.json  →  participant_pipeline: [{ "participant_id": "P001" }]
       participants.json  →  find P001  →  "Sarah Chen"
    """
    projects     = _load_projects()
    participants = _load_participants()   # 💡 load BOTH files

    if not projects:
        return "No projects found. Create one first!"

    query_lower = query.lower()
    match = None

    for proj in projects:
        if proj["id"].lower() == query_lower or query_lower in proj["project_name"].lower():
            match = proj
            break

    if not match:
        return f"No project found matching '{query}'."

    # Format screening criteria nicely
    sc = match.get("screening_criteria", {})
    criteria_lines = []
    if sc.get("job_role"):        criteria_lines.append(f"Role: {sc['job_role']}")
    if sc.get("seniority_level"): criteria_lines.append(f"Seniority: {sc['seniority_level']}")
    if sc.get("methods"):         criteria_lines.append(f"Methods: {', '.join(sc['methods'])}")
    if sc.get("availability"):    criteria_lines.append(f"Availability: {sc['availability']}")
    criteria_text = " | ".join(criteria_lines) if criteria_lines else "none specified"

    # 💡 Cross-reference: turn participant IDs → names
    pipeline = match.get("participant_pipeline", [])
    if pipeline:
        pipeline_lines = []
        for entry in pipeline:
            name = _participant_name(entry["participant_id"], participants)
            pipeline_lines.append(f"  • {name} ({entry['participant_id']}) — {entry['status']}")
        pipeline_text = "\n".join(pipeline_lines)
    else:
        pipeline_text = "  No participants added yet — run screening in Phase 3!"

    # Progress towards target — e.g. "2 of 5 completed"
    # 💡 .get() with a default handles projects created before this field existed
    target    = match.get("target_participants", "not set")
    completed = sum(1 for e in pipeline if e.get("status") == "completed")
    progress  = f"{completed} of {target} completed" if isinstance(target, int) else "target not set"

    return (
        f"ID: {match['id']}\n"
        f"Project: {match['project_name']}\n"
        f"Goal: {match['research_goal']}\n"
        f"Status: {match['project_status']}\n"
        f"Progress: {progress}\n"
        f"Screening criteria: {criteria_text}\n"
        f"Participant pipeline:\n{pipeline_text}\n"
        f"Notes: {match['notes'] or 'none'}\n"
        f"Created: {match['date_created']}"
    )


def screen_participants(project_id: str) -> str:
    """
    Loads the project's screening criteria + all active participants
    and returns them formatted for Claude to reason about.

    💡 THERE IS NO RANKING LOGIC IN THIS FUNCTION.
       It just fetches and formats data. Claude reads this output
       and decides who fits — like a human researcher reading CVs.

       This is the key difference from traditional code:
       Instead of writing rules (if seniority == "Senior"...),
       we describe what we want and let Claude judge.
    """
    projects     = _load_projects()
    participants = _load_participants()

    # Find the project
    project = next((p for p in projects if p["id"] == project_id), None)
    if not project:
        return f"Project '{project_id}' not found."

    # Only show active participants (skip inactive / do-not-contact)
    active = [p for p in participants if p["status"] == "active"]
    if not active:
        return "No active participants in the panel yet."

    # Format the project criteria clearly
    sc = project.get("screening_criteria", {})
    criteria_parts = []
    if sc.get("job_role"):        criteria_parts.append(f"Role: {sc['job_role']}")
    if sc.get("seniority_level"): criteria_parts.append(f"Seniority: {sc['seniority_level']}")
    if sc.get("methods"):         criteria_parts.append(f"Methods: {', '.join(sc['methods'])}")
    if sc.get("availability"):    criteria_parts.append(f"Availability: {sc['availability']}")

    lines = [
        f"PROJECT: {project['project_name']} ({project['id']})",
        f"Goal: {project['research_goal']}",
        f"Looking for: {' | '.join(criteria_parts)}",
        "",
        f"PARTICIPANTS TO SCREEN ({len(active)} active):",
        "─" * 40,
    ]

    # Format each participant as a single readable line
    for p in active:
        methods  = ", ".join(p["preferred_methods"]) if p["preferred_methods"] else "none"
        sessions = len(p["participation_history"])
        lines.append(
            f"{p['id']} | {p['name']} | {p['job_role']} | {p['seniority_level']} | "
            f"Methods: {methods} | Availability: {p['availability']} | "
            f"Sessions done: {sessions}"
        )

    lines += [
        "─" * 40,
        "Please assess each participant's fit against the criteria above.",
        "Call add_to_pipeline for each one you decide to shortlist.",
    ]

    return "\n".join(lines)


def add_to_pipeline(project_id: str, participant_id: str, status: str) -> str:
    """
    Saves Claude's screening decision to the project's participant_pipeline.

    💡 HOW IT WORKS:
       - If the participant is already in the pipeline, update their status
       - If they're new, add them
       This means you can call it multiple times — it won't create duplicates.
    """
    valid_statuses = {"shortlisted", "invited", "confirmed", "completed", "declined"}
    if status not in valid_statuses:
        return f"Invalid status '{status}'. Use: {', '.join(valid_statuses)}"

    projects     = _load_projects()
    participants = _load_participants()

    # Find the project
    project = next((p for p in projects if p["id"] == project_id), None)
    if not project:
        return f"Project '{project_id}' not found."

    # Check participant exists
    participant = next((p for p in participants if p["id"] == participant_id), None)
    if not participant:
        return f"Participant '{participant_id}' not found."

    pipeline = project.setdefault("participant_pipeline", [])

    # Update if already in pipeline, otherwise add
    existing = next((e for e in pipeline if e["participant_id"] == participant_id), None)
    if existing:
        existing["status"] = status
        action = "Updated"
    else:
        pipeline.append({
            "participant_id": participant_id,
            "status":         status,
            "date_added":     str(date.today())
        })
        action = "Added"

    _save_projects(projects)
    return f"{action} {participant['name']} ({participant_id}) → {status} in {project['project_name']}."


def draft_outreach_email(project_id: str, participant_id: str) -> str:
    """
    Fetches the participant's profile + project details and returns
    them as context for Claude to write a personalised email.

    💡 SAME PATTERN AS screen_participants:
       The function fetches data.
       Claude writes the email.

       There's no email template in this code — Claude composes
       a fresh, personalised email every time based on the real
       details of this specific person and project.
    """
    projects     = _load_projects()
    participants = _load_participants()

    project     = next((p for p in projects     if p["id"] == project_id),     None)
    participant = next((p for p in participants if p["id"] == participant_id), None)

    if not project:
        return f"Project '{project_id}' not found."
    if not participant:
        return f"Participant '{participant_id}' not found."

    methods  = ", ".join(participant["preferred_methods"]) if participant["preferred_methods"] else "not specified"
    sessions = len(participant["participation_history"])

    sc = project.get("screening_criteria", {})
    study_method = ", ".join(sc.get("methods", [])) if sc.get("methods") else "research session"

    return (
        f"PARTICIPANT\n"
        f"Name: {participant['name']}\n"
        f"Email: {participant['email']}\n"
        f"Role: {participant['job_role']} ({participant['seniority_level']})\n"
        f"Organisation: {participant['organisation'] or 'not specified'}\n"
        f"Preferred methods: {methods}\n"
        f"Availability: {participant['availability']}\n"
        f"Past sessions with us: {sessions}\n"
        f"Notes: {participant['notes'] or 'none'}\n"
        f"\n"
        f"PROJECT\n"
        f"Name: {project['project_name']}\n"
        f"Goal: {project['research_goal']}\n"
        f"Session type: {study_method}\n"
        f"Notes: {project['notes'] or 'none'}\n"
        f"\n"
        f"Please draft a warm, personalised outreach email inviting this participant to the study. "
        f"Reference their role and the research goal naturally. Keep it concise (3–4 short paragraphs). "
        f"End with a clear call to action. Do not use a generic template tone.\n"
        f"{_format_insights_for_email(participant)}"
    )


def record_session(
    project_id: str,
    participant_id: str,
    touchpoint_type: str,
    notes: str = ""
) -> str:
    """
    Records a completed research session.

    💡 NEW CONCEPT — updating nested data (a list inside an object):
       In Phase 1 we set simple fields like "status": "active".
       Now we APPEND a new item to participation_history, which is a
       list that lives INSIDE the participant object:

       participant {
         "participation_history": [        ← this list
           { "project_id": "PRJ-001", ... } ← we add one of these
         ]
       }

       In Python, appending to a list inside a dict looks like:
           participant["participation_history"].append({ ... })
       It's the same idea as push() in JavaScript arrays.

    This tool also updates TWO files at once — participants.json AND
    projects.json — because a session completion is relevant to both.
    """
    projects     = _load_projects()
    participants = _load_participants()

    project     = next((p for p in projects     if p["id"] == project_id),     None)
    participant = next((p for p in participants if p["id"] == participant_id), None)

    if not project:
        return f"Project '{project_id}' not found."
    if not participant:
        return f"Participant '{participant_id}' not found."

    today = str(date.today())

    # 1️⃣ Append to participant's participation_history
    #    💡 This is the nested list update — appending inside a list inside an object
    participant["participation_history"].append({
        "project_id":   project_id,
        "project_name": project["project_name"],
        "date":         today,
        "method":       touchpoint_type,
        "notes":        notes
    })

    # 2️⃣ Update last touchpoint fields on the participant
    participant["last_touchpoint"]      = touchpoint_type
    participant["last_touchpoint_date"] = today

    # 3️⃣ Update the project pipeline → mark as completed
    pipeline = project.get("participant_pipeline", [])
    entry = next((e for e in pipeline if e["participant_id"] == participant_id), None)
    if entry:
        entry["status"] = "completed"
    else:
        # If they weren't in the pipeline yet, add them as completed
        pipeline.append({
            "participant_id": participant_id,
            "status":         "completed",
            "date_added":     today
        })

    # 4️⃣ Save both files
    _save_participants(participants)
    _save_projects(projects)

    total_sessions = len(participant["participation_history"])
    return (
        f"✅ Recorded {touchpoint_type} session for {participant['name']} "
        f"on {today} ({project['project_name']}).\n"
        f"They've now completed {total_sessions} session(s) total."
    )


def get_participation_history(participant_id: str) -> str:
    """
    Returns a participant's full history across all projects.

    💡 This pulls from TWO sources:
       - participant.participation_history  → the session log
       - projects.json                      → to show project names (cross-referencing again!)
    """
    participants = _load_participants()

    # Support lookup by ID or name
    query_lower = participant_id.lower()
    participant = next(
        (p for p in participants
         if p["id"].lower() == query_lower or query_lower in p["name"].lower()),
        None
    )

    if not participant:
        return f"No participant found matching '{participant_id}'."

    history = participant["participation_history"]

    if not history:
        return (
            f"{participant['name']} ({participant['id']}) has no recorded sessions yet.\n"
            f"Last touchpoint: {participant['last_touchpoint'] or 'none'}"
        )

    lines = [
        f"Participation history for {participant['name']} ({participant['id']}):",
        f"Total sessions: {len(history)}",
        f"Last touchpoint: {participant['last_touchpoint']} on {participant['last_touchpoint_date']}",
        "─" * 40,
    ]

    # Show most recent first
    for entry in reversed(history):
        note_text = f" — {entry['notes']}" if entry.get("notes") else ""
        lines.append(f"• {entry['date']} | {entry['project_name']} | {entry['method']}{note_text}")

    return "\n".join(lines)


def panel_overview() -> str:
    """
    A research dashboard — gives a high-level view of the whole panel.

    💡 This is a "read-only" tool — it never writes anything.
       It just reads both JSON files and computes useful summaries.
       Claude can then answer natural questions like:
       "Who should we contact next?" or "How engaged is our panel?"
    """
    from datetime import datetime, timedelta

    participants = _load_participants()
    projects     = _load_projects()

    if not participants:
        return "The panel is empty — no participants added yet."

    today = date.today()

    # ── Participant stats ──
    active      = [p for p in participants if p["status"] == "active"]
    inactive    = [p for p in participants if p["status"] == "inactive"]
    do_not      = [p for p in participants if p["status"] == "do-not-contact"]

    never_contacted = [p for p in active if not p["last_touchpoint_date"]]

    # Participants not contacted in the last 60 days
    stale_threshold = today - timedelta(days=60)
    stale = [
        p for p in active
        if p["last_touchpoint_date"] and
        datetime.strptime(p["last_touchpoint_date"], "%Y-%m-%d").date() < stale_threshold
    ]

    # Most experienced participants (sorted by sessions done)
    by_sessions = sorted(active, key=lambda p: len(p["participation_history"]), reverse=True)
    top = by_sessions[:3]

    # ── Project pipeline stats ──
    pipeline_summary = []
    for proj in projects:
        pipeline = proj.get("participant_pipeline", [])
        if pipeline:
            counts = {}
            for entry in pipeline:
                counts[entry["status"]] = counts.get(entry["status"], 0) + 1
            status_text = ", ".join(f"{v} {k}" for k, v in counts.items())
            pipeline_summary.append(f"  • {proj['project_name']} ({proj['id']}): {status_text}")

    # ── Build the overview ──
    lines = [
        "╔══════════════════════════════╗",
        "       PANEL OVERVIEW",
        "╚══════════════════════════════╝",
        "",
        f"👥 Total participants: {len(participants)}",
        f"   Active: {len(active)} | Inactive: {len(inactive)} | Do-not-contact: {len(do_not)}",
        "",
        f"📭 Never contacted: {len(never_contacted)}",
    ]
    if never_contacted:
        for p in never_contacted:
            lines.append(f"   • {p['name']} ({p['job_role']})")

    lines += [
        "",
        f"⏰ Not contacted in 60+ days: {len(stale)}",
    ]
    if stale:
        for p in stale:
            lines.append(f"   • {p['name']} — last: {p['last_touchpoint_date']}")

    lines += [
        "",
        "🏆 Most experienced participants:",
    ]
    for p in top:
        sessions = len(p["participation_history"])
        lines.append(f"   • {p['name']} — {sessions} session(s)")

    if pipeline_summary:
        lines += ["", "📋 Project pipelines:"]
        lines += pipeline_summary

    return "\n".join(lines)


def send_outreach_email(
    participant_id: str,
    project_id: str,
    subject: str,
    body: str
) -> str:
    """
    Sends an outreach email via the Resend API, then updates the participant's
    pipeline status to 'invited' and records the touchpoint.

    💡 HOW THIS FITS THE HUMAN-IN-THE-LOOP PATTERN:
       This function is intentionally separate from draft_outreach_email.
       The researcher always sees the draft first, then decides to send.
       Claude only calls this tool when the researcher explicitly approves.

    💡 HOW THE RESEND SDK WORKS:
       Similar to the Anthropic SDK — you set an API key, then call a method.
         resend.api_key = "re_..."
         resend.Emails.send({ "from": ..., "to": ..., "subject": ..., "html": ... })
       That's it. The SDK handles all the HTTP stuff.

    💡 RESEND_FROM_EMAIL:
       Without a verified domain → "onboarding@resend.dev" (test mode, sends to your email only)
       With a verified domain    → "you@yourdomain.com" (sends to anyone)
    """
    import resend
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BASE_DIR, ".env.local"))

    api_key   = os.getenv("RESEND_API_KEY",     "")
    from_email = os.getenv("RESEND_FROM_EMAIL", "onboarding@resend.dev")

    if not api_key:
        return (
            "⚠️  RESEND_API_KEY is not set.\n"
            "Add it to .env.local — get a free key at https://resend.com"
        )

    participants = _load_participants()
    projects     = _load_projects()

    query_lower = participant_id.lower()
    participant = next(
        (p for p in participants
         if p["id"].lower() == query_lower or query_lower in p["name"].lower()),
        None
    )
    project = next((p for p in projects if p["id"] == project_id), None)

    if not participant:
        return f"Participant '{participant_id}' not found."
    if not project:
        return f"Project '{project_id}' not found."

    to_email = participant["email"]

    # Convert plain text to simple HTML
    # (Resend requires HTML; we wrap paragraphs in <p> tags)
    html_body = "".join(
        f"<p>{line}</p>" if line.strip() else "<br>"
        for line in body.splitlines()
    )

    try:
        resend.api_key = api_key

        resend.Emails.send({
            "from":    from_email,
            "to":      [to_email],
            "subject": subject,
            "html":    html_body,
            "reply_to": from_email,
        })

        # ── Update participant record ──────────────────────────────
        today = str(date.today())
        participant["last_touchpoint"]      = "email"
        participant["last_touchpoint_date"] = today

        # ── Update pipeline status → invited ──────────────────────
        pipeline = project.get("participant_pipeline", [])
        entry = next((e for e in pipeline if e["participant_id"] == participant["id"]), None)
        if entry:
            entry["status"] = "invited"
        else:
            pipeline.append({
                "participant_id": participant["id"],
                "status":         "invited",
                "date_added":     today,
            })

        _save_participants(participants)
        _save_projects(projects)

        return (
            f"✅ Email sent to {participant['name']} ({to_email}).\n"
            f"   Subject: {subject}\n"
            f"   Pipeline status updated → invited."
        )

    except Exception as e:
        return f"❌ Failed to send email: {str(e)}"


def add_organisation(
    name: str,
    sector: str,
    size: str,
    website: str = "",
    notes: str = ""
) -> str:
    """
    Adds a new organisation to organisations.json.

    💡 NEW CONCEPT — a third JSON file joining the family:
       We now have three files that reference each other:
         participants.json  ← participant has organisation_id
              ↓
         organisations.json ← org record lives here
              ↑
         projects.json      ← could also reference orgs later

       This is how relational databases work — each table stores
       its own data, and foreign keys (IDs) link them together.
       Our JSON files are doing the same thing, just simpler.
    """
    organisations = _load_organisations()

    # Prevent duplicate names (case-insensitive)
    for org in organisations:
        if org["name"].lower() == name.lower():
            return f"An organisation named '{name}' already exists (ID: {org['id']})."

    valid_sizes = {"startup", "sme", "enterprise"}
    if size.lower() not in valid_sizes:
        return f"Invalid size '{size}'. Use: startup, SME, or enterprise."

    new_org = {
        "id":         _generate_org_id(organisations),
        "name":       name,
        "sector":     sector,
        "size":       size.lower(),
        "website":    website,
        "notes":      notes,
        "date_added": str(date.today())
    }

    organisations.append(new_org)
    _save_organisations(organisations)

    return f"✅ Added organisation '{name}' (ID: {new_org['id']})."


def get_organisation(query: str) -> str:
    """
    Looks up an organisation by ID or name.

    💡 THE CROSS-REFERENCE MOMENT:
       This is the same pattern as get_project showing participant names —
       but now going the other direction. Given an org, we find all
       participants whose organisation_id matches.

       It's the relational lookup that makes the directory useful:
       "Show me all the Spotify researchers we've worked with."
    """
    organisations = _load_organisations()
    participants  = _load_participants()

    query_lower = query.lower()
    org = next(
        (o for o in organisations
         if o["id"].lower() == query_lower or query_lower in o["name"].lower()),
        None
    )
    if not org:
        return f"No organisation found matching '{query}'."

    # Find all participants linked to this org by organisation_id
    linked = [p for p in participants if p.get("organisation_id") == org["id"]]

    lines = [
        f"ID: {org['id']}",
        f"Name: {org['name']}",
        f"Sector: {org['sector']}",
        f"Size: {org['size']}",
        f"Website: {org['website'] or 'not set'}",
        f"Notes: {org['notes'] or 'none'}",
        f"Date added: {org['date_added']}",
        f"",
        f"Linked participants ({len(linked)}):",
    ]

    if linked:
        for p in linked:
            sessions = len(p.get("participation_history", []))
            lines.append(
                f"  • {p['name']} ({p['id']}) — {p['job_role']}, {p['seniority_level']} "
                f"| {sessions} session(s) | Status: {p['status']}"
            )
    else:
        lines.append("  None linked yet — use update_participant with organisation_id to link people.")

    return "\n".join(lines)


def list_organisations() -> str:
    """Lists all organisations with their participant counts."""
    organisations = _load_organisations()
    participants  = _load_participants()

    if not organisations:
        return "No organisations added yet. Use add_organisation to register companies."

    lines = [f"Organisations ({len(organisations)} total):\n"]
    for org in organisations:
        count = sum(1 for p in participants if p.get("organisation_id") == org["id"])
        lines.append(
            f"• {org['id']} — {org['name']} | {org['sector']} | {org['size']} "
            f"| {count} linked participant(s)"
        )

    return "\n".join(lines)


def import_participants_csv(file_path: str) -> str:
    """
    Reads a CSV file and bulk-adds participants to the panel.

    💡 NEW CONCEPT — the csv module:
       Python has a built-in csv module (no installation needed).
       csv.DictReader reads each row as a dictionary, so you can
       access columns by name: row["email"], row["job_role"], etc.
       It's like reading a spreadsheet row by row.

    💡 THE PREFERRED_METHODS PARSING TRICK:
       In JSON, methods are a list: ["interview", "usability test"]
       In CSV, they're a comma-separated string in one cell: "interview, usability test"
       We split the string back into a list so it matches our schema.

    💡 GRACEFUL HANDLING:
       Rather than crashing on the first bad row, we collect all
       results (added / skipped / errors) and return a full summary.
       This way a typo in one row doesn't block the whole import.
    """
    import csv

    # Support relative paths — resolves to the project folder
    if not os.path.isabs(file_path):
        file_path = os.path.join(BASE_DIR, file_path)

    if not os.path.exists(file_path):
        return (
            f"File not found: '{file_path}'.\n"
            f"Make sure the CSV is in the project folder or provide the full path."
        )

    required_columns = {"name", "email", "job_role", "seniority_level", "preferred_methods", "availability"}

    try:
        # utf-8-sig handles the invisible BOM character Excel sometimes adds
        with open(file_path, "r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)

            # Check all required columns are present
            # .lower() so "Name" and "name" both work
            fieldnames_lower = {col.strip().lower() for col in (reader.fieldnames or [])}
            missing = required_columns - fieldnames_lower
            if missing:
                return (
                    f"Missing required columns: {', '.join(sorted(missing))}.\n"
                    f"Check your CSV against data/sample_participants.csv."
                )

            added   = []
            skipped = []
            errors  = []

            for i, row in enumerate(reader, start=2):  # start=2 — row 1 is the header
                # Strip whitespace from every value in the row
                row = {k: (v.strip() if v else "") for k, v in row.items()}

                name  = row.get("name",  "")
                email = row.get("email", "")

                if not name or not email:
                    errors.append(f"Row {i}: missing name or email — skipped")
                    continue

                # "interview, usability test" → ["interview", "usability test"]
                methods_raw = row.get("preferred_methods", "")
                methods = [m.strip() for m in methods_raw.split(",") if m.strip()]

                result = add_participant(
                    name             = name,
                    email            = email,
                    job_role         = row.get("job_role",         ""),
                    seniority_level  = row.get("seniority_level",  ""),
                    preferred_methods = methods,
                    availability     = row.get("availability",     ""),
                    persona          = row.get("persona",          ""),
                    organisation     = row.get("organisation",     ""),
                    notes            = row.get("notes",            ""),
                )

                if result.startswith("✅"):
                    added.append(name)
                elif "already exists" in result:
                    skipped.append(name)
                else:
                    errors.append(f"Row {i} ({name}): {result}")

        # Build a clear summary
        lines = ["CSV import complete:"]
        if added:
            lines.append(f"  ✅ Added {len(added)}: {', '.join(added)}")
        if skipped:
            lines.append(f"  ⏭️  Skipped {len(skipped)} (already in panel): {', '.join(skipped)}")
        if errors:
            lines.append(f"  ❌ {len(errors)} error(s):")
            for e in errors:
                lines.append(f"     {e}")
        if not added and not skipped and not errors:
            lines.append("  No rows found — is the file empty?")

        return "\n".join(lines)

    except Exception as e:
        return f"Error reading CSV: {str(e)}"


def update_participant(
    participant_id: str,
    name: str = None,
    email: str = None,
    job_role: str = None,
    persona: str = None,
    organisation: str = None,
    organisation_id: str = None,
    seniority_level: str = None,
    preferred_methods: list = None,
    availability: str = None,
    status: str = None,
    notes: str = None
) -> str:
    """
    Updates one or more fields on a participant's profile.

    💡 NEW CONCEPT — partial updates:
       Every parameter except participant_id defaults to None.
       We only overwrite a field if a new value was actually provided.

       In Python, this pattern looks like:
           if name is not None:
               participant["name"] = name

       This means you can update just one field (e.g. status)
       without accidentally wiping out everything else.
       Same idea as a PATCH request in web APIs — change only what's sent.

    💡 STATUS VALIDATION:
       "status" is the one field we validate strictly because a wrong
       value (e.g. "unavailable") would silently break panel_overview's
       filtering logic. All other fields are free-text so no validation needed.
    """
    participants = _load_participants()

    # Find by ID or name
    query_lower = participant_id.lower()
    participant = next(
        (p for p in participants
         if p["id"].lower() == query_lower or query_lower in p["name"].lower()),
        None
    )

    if not participant:
        return f"No participant found matching '{participant_id}'."

    # Validate status before making any changes
    valid_statuses = {"active", "inactive", "do-not-contact"}
    if status is not None and status not in valid_statuses:
        return f"Invalid status '{status}'. Use: active, inactive, or do-not-contact."

    # Build a log of what actually changed — useful for the confirmation message
    changes = []

    # Handle organisation_id — look up the org name and set both fields
    # 💡 This is the relational link in action:
    #    Setting organisation_id also updates the display name automatically
    #    so get_participant still shows "Spotify" not just "ORG-001"
    if organisation_id is not None:
        organisations = _load_organisations()
        org = next((o for o in organisations if o["id"] == organisation_id), None)
        if not org:
            return f"Organisation ID '{organisation_id}' not found. Use list_organisations to see valid IDs."
        participant["organisation_id"] = organisation_id
        participant["organisation"]    = org["name"]   # keep display name in sync
        changes.append(f"organisation → {org['name']} (linked as {organisation_id})")

    # Update only the fields that were provided (not None)
    # 💡 This is the partial update pattern — only touch what's sent
    if name              is not None: participant["name"]              = name;              changes.append(f"name → {name}")
    if email             is not None: participant["email"]             = email;             changes.append(f"email → {email}")
    if job_role          is not None: participant["job_role"]          = job_role;          changes.append(f"job_role → {job_role}")
    if persona           is not None: participant["persona"]           = persona;           changes.append(f"persona → {persona}")
    if organisation      is not None: participant["organisation"]      = organisation;      changes.append(f"organisation → {organisation}")
    if seniority_level   is not None: participant["seniority_level"]   = seniority_level;   changes.append(f"seniority_level → {seniority_level}")
    if preferred_methods is not None: participant["preferred_methods"] = preferred_methods; changes.append(f"preferred_methods → {preferred_methods}")
    if availability      is not None: participant["availability"]      = availability;      changes.append(f"availability → {availability}")
    if status            is not None: participant["status"]            = status;            changes.append(f"status → {status}")
    if notes             is not None: participant["notes"]             = notes;             changes.append(f"notes updated")

    if not changes:
        return "No changes provided — nothing was updated."

    _save_participants(participants)

    changes_text = "\n  ".join(changes)
    return f"✅ Updated {participant['name']} ({participant['id']}):\n  {changes_text}"


def list_projects() -> str:
    """
    Returns a quick overview of all projects — useful before diving into
    a specific project summary, or just to see what's running.
    """
    projects     = _load_projects()
    participants = _load_participants()

    if not projects:
        return "No projects yet. Create one with create_project!"

    lines = [f"Found {len(projects)} project(s):\n"]

    for proj in projects:
        pipeline  = proj.get("participant_pipeline", [])
        target    = proj.get("target_participants", "?")
        completed = sum(1 for e in pipeline if e.get("status") == "completed")
        active    = sum(1 for e in pipeline if e.get("status") in {"shortlisted", "invited", "confirmed"})

        lines.append(
            f"• {proj['id']} — {proj['project_name']} | "
            f"Status: {proj['project_status']} | "
            f"Progress: {completed}/{target} completed | "
            f"{active} in pipeline"
        )

    return "\n".join(lines)


def get_project_summary(project_id: str) -> str:
    """
    Builds a detailed research ops summary for a project.

    💡 SAME PATTERN AS panel_overview — read-only, no writes.
       This function fetches and formats the data.
       Claude reads it and adds:
         - Plain-language status summary
         - Pattern observations from session insights
         - Single most important next action

       The combination of structured data (this function)
       + natural language reasoning (Claude) is what makes
       the summary genuinely useful rather than just a report.
    """
    from datetime import datetime

    projects     = _load_projects()
    participants = _load_participants()

    project = next((p for p in projects if p["id"] == project_id), None)
    if not project:
        return f"Project '{project_id}' not found."

    pipeline = project.get("participant_pipeline", [])
    target   = project.get("target_participants", None)

    # ── Pipeline funnel counts ──────────────────────────────
    statuses  = ["shortlisted", "invited", "confirmed", "completed", "declined"]
    counts    = {s: 0 for s in statuses}
    for entry in pipeline:
        s = entry.get("status", "")
        if s in counts:
            counts[s] += 1

    completed     = counts["completed"]
    still_needed  = (target - completed) if target else "unknown"
    pct           = f"{int(completed / target * 100)}%" if target else "n/a"

    # ── Pipeline detail with days-since-action ──────────────
    # 💡 "Days since added" flags who's been sitting in shortlisted
    #    without being contacted — a real research ops pain point
    today          = datetime.today().date()
    pipeline_lines = []

    for entry in pipeline:
        p_id    = entry["participant_id"]
        p_name  = _participant_name(p_id, participants)
        status  = entry["status"]
        added   = entry.get("date_added", "")

        days_text = ""
        if added:
            delta     = (today - datetime.strptime(added, "%Y-%m-%d").date()).days
            days_text = f" | {delta}d ago"

        status_icon = {
            "shortlisted": "📋", "invited": "📨",
            "confirmed": "✅", "completed": "🎉", "declined": "❌"
        }.get(status, "•")

        pipeline_lines.append(
            f"  {status_icon} {p_name} ({p_id}) — {status}{days_text}"
        )

    # ── Session insights from completed participants ─────────
    # 💡 This is where project summary connects to participant summary —
    #    we pull Phase 5 insights into the project-level view
    insight_lines = []
    for entry in pipeline:
        if entry.get("status") != "completed":
            continue
        participant = next(
            (p for p in participants if p["id"] == entry["participant_id"]), None
        )
        if not participant:
            continue
        session_insights = participant.get("session_insights", [])
        proj_insights    = next(
            (s for s in session_insights if s["project_id"] == project_id), None
        )
        if not proj_insights or not proj_insights.get("key_insights"):
            continue

        insight_lines.append(f"\n  From {participant['name']}:")
        for insight in proj_insights["key_insights"]:
            insight_lines.append(f"    • {insight}")
        for quote in proj_insights.get("quotes", []):
            insight_lines.append(f'    "{quote}"')

    # ── Build the full output ────────────────────────────────
    lines = [
        f"PROJECT SUMMARY — {project['project_name']} ({project['id']})",
        "═" * 50,
        f"Goal:    {project['research_goal']}",
        f"Status:  {project['project_status']}",
        f"Target:  {target} participants",
        "",
        "PROGRESS",
        "─" * 20,
        f"Completed:   {completed} / {target}  ({pct})",
        f"Still needed: {still_needed}",
        f"Shortlisted:  {counts['shortlisted']}",
        f"Invited:      {counts['invited']}",
        f"Confirmed:    {counts['confirmed']}",
        f"Declined:     {counts['declined']}",
        "",
        "PIPELINE",
        "─" * 20,
    ]
    lines += pipeline_lines if pipeline_lines else ["  No participants yet."]

    if insight_lines:
        lines += ["", "SESSION INSIGHTS SO FAR", "─" * 20]
        lines += insight_lines

    lines += [
        "",
        "─" * 50,
        "Please give a concise research ops status update in plain language.",
        "Highlight anything that needs attention and suggest the single most important next action.",
    ]

    return "\n".join(lines)


def add_session_notes(participant_id: str, project_id: str, raw_notes: str) -> str:
    """
    Saves raw session notes to the participant's profile.

    💡 THIS IS THE DATA HALF of the participant summary feature.
       The intelligence half happens in Claude — it reads what this
       function returns, then calls save_session_summary with its
       structured extraction.

       Raw notes stay in the profile too, so nothing is lost.
       The structured summary is what gets used for outreach later.
    """
    participants = _load_participants()
    projects     = _load_projects()

    query_lower = participant_id.lower()
    participant = next(
        (p for p in participants
         if p["id"].lower() == query_lower or query_lower in p["name"].lower()),
        None
    )
    project = next((p for p in projects if p["id"] == project_id), None)

    if not participant:
        return f"No participant found matching '{participant_id}'."
    if not project:
        return f"Project '{project_id}' not found."

    # Add session_insights list if the participant was added before this feature
    # 💡 This is called a "migration" — adding a new field to existing data
    #    gracefully, without breaking anything that's already there.
    if "session_insights" not in participant:
        participant["session_insights"] = []

    # Save the raw notes under the right project entry
    # Check if an entry for this project already exists
    existing = next(
        (s for s in participant["session_insights"] if s["project_id"] == project_id),
        None
    )
    if existing:
        existing["raw_notes"] = raw_notes
        existing["date"]      = str(date.today())
    else:
        participant["session_insights"].append({
            "project_id":      project_id,
            "project_name":    project["project_name"],
            "date":            str(date.today()),
            "raw_notes":       raw_notes,
            "key_insights":    [],
            "follow_up_items": [],
            "quotes":          []
        })

    _save_participants(participants)

    return (
        f"✅ Saved raw notes for {participant['name']} ({project['project_name']}).\n\n"
        f"RAW NOTES TO SUMMARISE:\n"
        f"{'─' * 40}\n"
        f"{raw_notes}\n"
        f"{'─' * 40}\n\n"
        f"Please now call save_session_summary with your structured extraction "
        f"of key insights, follow-up items, and notable quotes from these notes."
    )


def save_session_summary(
    participant_id: str,
    project_id: str,
    key_insights: list,
    follow_up_items: list,
    quotes: list = None
) -> str:
    """
    Saves Claude's structured extraction back to the participant's profile.

    💡 THIS IS THE INTELLIGENCE HALF of the participant summary feature.
       Claude calls this after reading the raw notes from add_session_notes.
       Together, add_session_notes → Claude reads → save_session_summary
       is the same tool-chaining pattern from Phase 3, applied to synthesis.
    """
    participants = _load_participants()

    query_lower = participant_id.lower()
    participant = next(
        (p for p in participants
         if p["id"].lower() == query_lower or query_lower in p["name"].lower()),
        None
    )
    if not participant:
        return f"No participant found matching '{participant_id}'."

    insights_list = participant.get("session_insights", [])
    entry = next((s for s in insights_list if s["project_id"] == project_id), None)

    if not entry:
        return f"No session notes found for project '{project_id}'. Call add_session_notes first."

    entry["key_insights"]    = key_insights
    entry["follow_up_items"] = follow_up_items
    entry["quotes"]          = quotes or []

    _save_participants(participants)

    return (
        f"✅ Saved session summary for {participant['name']}:\n"
        f"  {len(key_insights)} insight(s), "
        f"{len(follow_up_items)} follow-up item(s), "
        f"{len(quotes or [])} quote(s)."
    )


def get_participant_summary(participant_id: str) -> str:
    """
    Returns all stored session insights for a participant across all projects.

    💡 THIS IS WHAT MAKES OUTREACH PERSONAL:
       When draft_outreach_email fetches this context, Claude can reference
       real things the participant said or flagged in previous sessions —
       not just their profile fields.

       "Following up on the checkout friction point you mentioned last time..."
       is only possible because this function exists.
    """
    participants = _load_participants()

    query_lower = participant_id.lower()
    participant = next(
        (p for p in participants
         if p["id"].lower() == query_lower or query_lower in p["name"].lower()),
        None
    )
    if not participant:
        return f"No participant found matching '{participant_id}'."

    insights_list = participant.get("session_insights", [])

    if not insights_list or not any(s["key_insights"] for s in insights_list):
        return (
            f"{participant['name']} has no session summaries yet. "
            f"Add notes with add_session_notes after their first session."
        )

    lines = [
        f"SESSION SUMMARIES — {participant['name']} ({participant['id']})",
        f"Total sessions with notes: {len(insights_list)}",
        "═" * 44,
    ]

    for entry in insights_list:
        lines += [
            f"\n📋 {entry['project_name']} | {entry['date']}",
            "─" * 40,
        ]

        if entry["key_insights"]:
            lines.append("Key insights:")
            for insight in entry["key_insights"]:
                lines.append(f"  • {insight}")

        if entry["follow_up_items"]:
            lines.append("Follow-up items:")
            for item in entry["follow_up_items"]:
                lines.append(f"  → {item}")

        if entry.get("quotes"):
            lines.append("Notable quotes:")
            for quote in entry["quotes"]:
                lines.append(f'  "{quote}"')

    return "\n".join(lines)


# ─────────────────────────────────────────────
# Tool dispatcher — same pattern as before!
# ─────────────────────────────────────────────

def run_tool(tool_name: str, tool_input: dict) -> str:
    """Looks up and runs a tool by name."""
    tool_functions = {
        "add_participant":    add_participant,
        "get_participant":    get_participant,
        "list_participants":  list_participants,
        "create_project":     create_project,       # Phase 2
        "get_project":        get_project,           # Phase 2
        "screen_participants":    screen_participants,    # Phase 3
        "add_to_pipeline":        add_to_pipeline,        # Phase 3
        "draft_outreach_email":   draft_outreach_email,   # Phase 3
        "record_session":            record_session,            # Phase 4
        "get_participation_history": get_participation_history, # Phase 4
        "panel_overview":            panel_overview,            # Phase 4
        "list_projects":             list_projects,             # Phase 6
        "get_project_summary":       get_project_summary,       # Phase 6
        "send_outreach_email":        send_outreach_email,        # Phase 8
        "import_participants_csv":   import_participants_csv,   # Phase 7
        "add_organisation":          add_organisation,          # Org schema
        "get_organisation":          get_organisation,          # Org schema
        "list_organisations":        list_organisations,        # Org schema
        "update_participant":        update_participant,        # Phase 4
        "add_session_notes":         add_session_notes,         # Phase 5
        "save_session_summary":      save_session_summary,      # Phase 5
        "get_participant_summary":   get_participant_summary,   # Phase 5
    }

    if tool_name not in tool_functions:
        return f"Error: tool '{tool_name}' not found."

    try:
        return tool_functions[tool_name](**tool_input)
    except Exception as e:
        return f"Error running '{tool_name}': {str(e)}"
