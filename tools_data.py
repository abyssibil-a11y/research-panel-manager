# tools_data.py — Pure data layer
#
# 💡 WHAT THIS FILE IS FOR:
#    This is the data layer of the refactored architecture.
#    Every function here does one thing: read or write JSON files.
#
#    Rules this file must always follow:
#      ✅ Returns structured data (dicts, lists, booleans)
#      ✅ No conversational strings ("Here are your results...")
#      ✅ No Claude API calls — zero AI logic
#      ✅ Each function is independently testable
#
#    The conversational wrappers (for the Gradio UI) stay in tools.py.
#    The MCP server will import directly from here.
#
# 💡 RETURN CONVENTION:
#    Read operations  → return the data itself (dict / list / None)
#    Write operations → return {"success": bool, ...extra fields..., "error": str}
#
#    This mirrors the pattern used by REST APIs:
#      GET  /participants/P001  →  returns the participant object (or 404)
#      POST /participants        →  returns {"id": "P001", "success": true}
#      PATCH /participants/P001 →  returns {"success": true, "changes": [...]}

import csv
import json
import os
from datetime import date, datetime, timedelta
from typing import Optional


# ─────────────────────────────────────────────
# File paths
# ─────────────────────────────────────────────

BASE_DIR           = os.path.dirname(__file__)
PARTICIPANTS_FILE  = os.path.join(BASE_DIR, "data", "participants.json")
PROJECTS_FILE      = os.path.join(BASE_DIR, "data", "projects.json")
ORGANISATIONS_FILE = os.path.join(BASE_DIR, "data", "organisations.json")


# ─────────────────────────────────────────────
# Private helpers — load, save, generate IDs
# (same as before, just centralised here)
# ─────────────────────────────────────────────

def _load_participants() -> list:
    with open(PARTICIPANTS_FILE, "r") as f:
        data = json.load(f)
    return data if data else []


def _save_participants(participants: list):
    with open(PARTICIPANTS_FILE, "w") as f:
        json.dump(participants, f, indent=2)


def _generate_participant_id(participants: list) -> str:
    next_number = len(participants) + 1
    return f"P{next_number:03d}"


def _load_projects() -> list:
    with open(PROJECTS_FILE, "r") as f:
        data = json.load(f)
    return data if data else []


def _save_projects(projects: list):
    with open(PROJECTS_FILE, "w") as f:
        json.dump(projects, f, indent=2)


def _generate_project_id(projects: list) -> str:
    next_number = len(projects) + 1
    return f"PRJ-{next_number:03d}"


def _load_organisations() -> list:
    with open(ORGANISATIONS_FILE, "r") as f:
        data = json.load(f)
    return data if data else []


def _save_organisations(organisations: list):
    with open(ORGANISATIONS_FILE, "w") as f:
        json.dump(organisations, f, indent=2)


def _generate_org_id(organisations: list) -> str:
    next_number = len(organisations) + 1
    return f"ORG-{next_number:03d}"


def _find_participant(query: str, participants: list) -> Optional[dict]:
    """
    Shared lookup used across many functions.
    Matches by exact ID or case-insensitive name substring.
    Returns the participant dict, or None if not found.
    """
    query_lower = query.lower()
    return next(
        (p for p in participants
         if p["id"].lower() == query_lower or query_lower in p["name"].lower()),
        None
    )


def _find_project(query: str, projects: list) -> Optional[dict]:
    """Matches by exact ID or case-insensitive name substring."""
    query_lower = query.lower()
    return next(
        (p for p in projects
         if p["id"].lower() == query_lower or query_lower in p["project_name"].lower()),
        None
    )


def _find_organisation(query: str, organisations: list) -> Optional[dict]:
    """Matches by exact ID or case-insensitive name substring."""
    query_lower = query.lower()
    return next(
        (o for o in organisations
         if o["id"].lower() == query_lower or query_lower in o["name"].lower()),
        None
    )


def get_past_session_context(participant: dict) -> dict:
    """
    Extracts follow-up items and quotes from a participant's session history.
    Used by the AI layer to personalise outreach emails.

    Returns:
        {
            "follow_up_items": [...],
            "quotes": [...]
        }
    """
    insights_list  = participant.get("session_insights", [])
    all_follow_ups = []
    all_quotes     = []

    for entry in insights_list:
        all_follow_ups.extend(entry.get("follow_up_items", []))
        all_quotes.extend(entry.get("quotes", []))

    return {
        "follow_up_items": all_follow_ups,
        "quotes":          all_quotes,
    }


# ─────────────────────────────────────────────
# Participants
# ─────────────────────────────────────────────

def get_all_participants(
    status: str   = "",
    job_role: str = "",
    method: str   = ""
) -> list:
    """
    Returns all participants, with optional filters.

    Args:
        status:   Filter by status string (e.g. "active", "do-not-contact")
        job_role: Filter by job role keyword (case-insensitive substring)
        method:   Filter by preferred method keyword (case-insensitive)

    Returns:
        List of participant dicts. Empty list if no matches.
    """
    participants = _load_participants()

    if status:
        participants = [p for p in participants if p["status"].lower() == status.lower()]

    if job_role:
        participants = [p for p in participants if job_role.lower() in p["job_role"].lower()]

    if method:
        participants = [
            p for p in participants
            if any(method.lower() in m.lower() for m in p["preferred_methods"])
        ]

    return participants


def get_participant_by_id(participant_id: str) -> Optional[dict]:
    """
    Fetch a single participant by ID or name.

    Returns:
        Participant dict, or None if not found.
    """
    participants = _load_participants()
    return _find_participant(participant_id, participants)


def add_participant(
    name: str,
    email: str,
    job_role: str,
    seniority_level: str,
    preferred_methods: list,
    availability: str,
    persona: str       = "",
    organisation: str  = "",
    notes: str         = ""
) -> dict:
    """
    Add a new participant to the panel.

    Returns:
        {
            "success":        bool,
            "participant_id": str,   # present on success
            "participant":    dict,  # full record, present on success
            "error":          str    # present on failure
        }
    """
    participants = _load_participants()

    # Prevent duplicate emails
    for p in participants:
        if p["email"].lower() == email.lower():
            return {
                "success": False,
                "error":   f"A participant with email '{email}' already exists (ID: {p['id']})."
            }

    new_participant = {
        "id":                   _generate_participant_id(participants),
        "name":                 name,
        "email":                email,
        "job_role":             job_role,
        "persona":              persona,
        "organisation":         organisation,
        "seniority_level":      seniority_level,
        "preferred_methods":    preferred_methods,
        "availability":         availability,
        "status":               "active",
        "last_touchpoint":      "",
        "last_touchpoint_date": "",
        "participation_history": [],
        "notes":                notes,
        "date_added":           str(date.today()),
    }

    participants.append(new_participant)
    _save_participants(participants)

    return {
        "success":        True,
        "participant_id": new_participant["id"],
        "participant":    new_participant,
    }


def update_participant(participant_id: str, updates: dict) -> dict:
    """
    Apply a partial update to a participant's profile.
    Only fields present in `updates` are changed — all others are untouched.

    💡 This is the PATCH pattern: send only what you want to change.

    Special case: if "organisation_id" is in updates, the function looks up
    the org name and keeps the display field in sync automatically.

    Returns:
        {
            "success":     bool,
            "participant": dict,   # updated record, present on success
            "changes":     list,   # human-readable list of what changed
            "error":       str     # present on failure
        }
    """
    participants = _load_participants()
    participant  = _find_participant(participant_id, participants)

    if not participant:
        return {"success": False, "error": f"No participant found matching '{participant_id}'."}

    valid_statuses = {"active", "inactive", "do-not-contact"}
    if "status" in updates and updates["status"] not in valid_statuses:
        return {
            "success": False,
            "error":   f"Invalid status '{updates['status']}'. Use: active, inactive, or do-not-contact."
        }

    changes = []

    # Special case: organisation_id also updates the display name
    if "organisation_id" in updates:
        organisations = _load_organisations()
        org = next((o for o in organisations if o["id"] == updates["organisation_id"]), None)
        if not org:
            return {
                "success": False,
                "error":   f"Organisation ID '{updates['organisation_id']}' not found."
            }
        participant["organisation_id"] = updates["organisation_id"]
        participant["organisation"]    = org["name"]
        changes.append(f"organisation → {org['name']} (linked as {updates['organisation_id']})")

    # Apply all other updates
    updatable_fields = [
        "name", "email", "job_role", "persona", "organisation",
        "seniority_level", "preferred_methods", "availability", "status", "notes"
    ]

    for field in updatable_fields:
        if field in updates:
            participant[field] = updates[field]
            changes.append(f"{field} → {updates[field]}")

    if not changes:
        return {"success": False, "error": "No valid fields provided — nothing was updated."}

    _save_participants(participants)

    return {
        "success":     True,
        "participant": participant,
        "changes":     changes,
    }


def get_participation_history(participant_id: str) -> dict:
    """
    Returns the full session history for a participant.

    Returns:
        {
            "success":      bool,
            "participant":  dict,    # basic profile info
            "history":      list,    # list of session dicts, most recent first
            "total":        int,
            "error":        str      # present on failure
        }
    """
    participants = _load_participants()
    participant  = _find_participant(participant_id, participants)

    if not participant:
        return {"success": False, "error": f"No participant found matching '{participant_id}'."}

    history = list(reversed(participant.get("participation_history", [])))

    return {
        "success":     True,
        "participant": {
            "id":                  participant["id"],
            "name":                participant["name"],
            "last_touchpoint":     participant["last_touchpoint"],
            "last_touchpoint_date":participant["last_touchpoint_date"],
        },
        "history": history,
        "total":   len(history),
    }


# ─────────────────────────────────────────────
# Projects
# ─────────────────────────────────────────────

def get_all_projects() -> list:
    """
    Returns all projects as a list of dicts.
    Each project dict includes a computed 'completed_count' field.
    """
    projects = _load_projects()

    # Add computed fields so callers don't have to recalculate
    for proj in projects:
        pipeline = proj.get("participant_pipeline", [])
        proj["completed_count"] = sum(1 for e in pipeline if e.get("status") == "completed")
        proj["pipeline_count"]  = len(pipeline)

    return projects


def get_project_by_id(project_id: str) -> Optional[dict]:
    """
    Fetch a single project by ID or name, with participant names resolved.

    Returns the project dict (with a 'pipeline_resolved' field that maps
    participant IDs to names), or None if not found.
    """
    projects     = _load_projects()
    participants = _load_participants()

    project = _find_project(project_id, projects)
    if not project:
        return None

    # Resolve participant IDs → names in the pipeline
    pipeline_resolved = []
    for entry in project.get("participant_pipeline", []):
        p = next((p for p in participants if p["id"] == entry["participant_id"]), None)
        pipeline_resolved.append({
            **entry,
            "name": p["name"] if p else f"Unknown ({entry['participant_id']})",
        })

    return {
        **project,
        "pipeline_resolved": pipeline_resolved,
    }


def create_project(
    project_name: str,
    research_goal: str,
    screening_criteria: dict,
    target_participants: int = 5,
    notes: str               = ""
) -> dict:
    """
    Create a new research project.

    Returns:
        {
            "success":    bool,
            "project_id": str,
            "project":    dict,
            "error":      str
        }
    """
    projects = _load_projects()

    new_project = {
        "id":                   _generate_project_id(projects),
        "project_name":         project_name,
        "research_goal":        research_goal,
        "project_status":       "draft",
        "target_participants":  target_participants,
        "screening_criteria":   screening_criteria,
        "participant_pipeline": [],
        "notes":                notes,
        "date_created":         str(date.today()),
    }

    projects.append(new_project)
    _save_projects(projects)

    return {
        "success":    True,
        "project_id": new_project["id"],
        "project":    new_project,
    }


def add_participant_to_pipeline(
    project_id: str,
    participant_id: str,
    status: str
) -> dict:
    """
    Add or update a participant in a project's pipeline.

    Returns:
        {
            "success":          bool,
            "action":           str,   # "added" or "updated"
            "participant_name": str,
            "project_name":     str,
            "status":           str,
            "error":            str    # present on failure
        }
    """
    valid_statuses = {"shortlisted", "invited", "confirmed", "completed", "declined"}
    if status not in valid_statuses:
        return {
            "success": False,
            "error":   f"Invalid status '{status}'. Use: {', '.join(valid_statuses)}"
        }

    projects     = _load_projects()
    participants = _load_participants()

    project     = _find_project(project_id, projects)
    participant = _find_participant(participant_id, participants)

    if not project:
        return {"success": False, "error": f"Project '{project_id}' not found."}
    if not participant:
        return {"success": False, "error": f"Participant '{participant_id}' not found."}

    pipeline = project.setdefault("participant_pipeline", [])
    existing = next((e for e in pipeline if e["participant_id"] == participant["id"]), None)

    if existing:
        existing["status"] = status
        action = "updated"
    else:
        pipeline.append({
            "participant_id": participant["id"],
            "status":         status,
            "date_added":     str(date.today()),
        })
        action = "added"

    _save_projects(projects)

    return {
        "success":          True,
        "action":           action,
        "participant_name": participant["name"],
        "project_name":     project["project_name"],
        "status":           status,
    }


def record_session(
    project_id: str,
    participant_id: str,
    touchpoint_type: str,
    notes: str = ""
) -> dict:
    """
    Record a completed research session.
    Updates the participant's history AND the project pipeline.

    Returns:
        {
            "success":        bool,
            "participant":    dict,  # updated profile
            "total_sessions": int,
            "error":          str
        }
    """
    projects     = _load_projects()
    participants = _load_participants()

    project     = _find_project(project_id, projects)
    participant = _find_participant(participant_id, participants)

    if not project:
        return {"success": False, "error": f"Project '{project_id}' not found."}
    if not participant:
        return {"success": False, "error": f"Participant '{participant_id}' not found."}

    today = str(date.today())

    # 1. Append to participant's history
    participant["participation_history"].append({
        "project_id":   project_id,
        "project_name": project["project_name"],
        "date":         today,
        "method":       touchpoint_type,
        "notes":        notes,
    })

    # 2. Update last touchpoint
    participant["last_touchpoint"]      = touchpoint_type
    participant["last_touchpoint_date"] = today

    # 3. Mark as completed in project pipeline
    pipeline = project.get("participant_pipeline", [])
    entry    = next((e for e in pipeline if e["participant_id"] == participant["id"]), None)
    if entry:
        entry["status"] = "completed"
    else:
        pipeline.append({
            "participant_id": participant["id"],
            "status":         "completed",
            "date_added":     today,
        })

    # 4. Save both files
    _save_participants(participants)
    _save_projects(projects)

    return {
        "success":        True,
        "participant":    participant,
        "total_sessions": len(participant["participation_history"]),
    }


def get_panel_stats() -> dict:
    """
    Compute summary statistics across the full panel and all projects.
    No AI — pure data aggregation. The AI layer turns this into prose.

    Returns:
        {
            "total":              int,
            "active":             int,
            "inactive":           int,
            "do_not_contact":     int,
            "never_contacted":    list of participant dicts,
            "stale":              list of participant dicts,  # not contacted in 60+ days
            "most_experienced":   list of participant dicts,  # top 3 by session count
            "project_pipelines":  list of {project_name, id, status_counts}
        }
    """
    participants = _load_participants()
    projects     = _load_projects()

    today           = date.today()
    stale_threshold = today - timedelta(days=60)

    active   = [p for p in participants if p["status"] == "active"]
    inactive = [p for p in participants if p["status"] == "inactive"]
    do_not   = [p for p in participants if p["status"] == "do-not-contact"]

    never_contacted = [p for p in active if not p["last_touchpoint_date"]]

    stale = [
        p for p in active
        if p["last_touchpoint_date"] and
        datetime.strptime(p["last_touchpoint_date"], "%Y-%m-%d").date() < stale_threshold
    ]

    most_experienced = sorted(
        active, key=lambda p: len(p["participation_history"]), reverse=True
    )[:3]

    project_pipelines = []
    for proj in projects:
        pipeline     = proj.get("participant_pipeline", [])
        status_counts = {}
        for entry in pipeline:
            s = entry["status"]
            status_counts[s] = status_counts.get(s, 0) + 1
        project_pipelines.append({
            "project_name":  proj["project_name"],
            "id":            proj["id"],
            "status":        proj["project_status"],
            "status_counts": status_counts,
        })

    return {
        "total":             len(participants),
        "active":            len(active),
        "inactive":          len(inactive),
        "do_not_contact":    len(do_not),
        "never_contacted":   never_contacted,
        "stale":             stale,
        "most_experienced":  most_experienced,
        "project_pipelines": project_pipelines,
    }


def get_project_data_for_screening(project_id: str) -> dict:
    """
    Fetch everything the AI layer needs to screen participants for a project:
    the project's criteria + all active participants.

    Returns:
        {
            "success":     bool,
            "project":     dict,
            "candidates":  list of participant dicts (active only),
            "error":       str
        }
    """
    projects     = _load_projects()
    participants = _load_participants()

    project = _find_project(project_id, projects)
    if not project:
        return {"success": False, "error": f"Project '{project_id}' not found."}

    candidates = [p for p in participants if p["status"] == "active"]

    return {
        "success":    True,
        "project":    project,
        "candidates": candidates,
    }


def get_project_data_for_email(project_id: str, participant_id: str) -> dict:
    """
    Fetch everything the AI layer needs to draft an outreach email:
    the participant's profile + the project details + past session context.

    Returns:
        {
            "success":        bool,
            "participant":    dict,
            "project":        dict,
            "past_context":   dict,  # follow_up_items and quotes from previous sessions
            "error":          str
        }
    """
    projects     = _load_projects()
    participants = _load_participants()

    project     = _find_project(project_id, projects)
    participant = _find_participant(participant_id, participants)

    if not project:
        return {"success": False, "error": f"Project '{project_id}' not found."}
    if not participant:
        return {"success": False, "error": f"Participant '{participant_id}' not found."}

    return {
        "success":      True,
        "participant":  participant,
        "project":      project,
        "past_context": get_past_session_context(participant),
    }


def get_project_data_for_summary(project_id: str) -> dict:
    """
    Fetch everything the AI layer needs to write a project status summary:
    full project record + pipeline resolved with names + collected insights.

    Returns:
        {
            "success":          bool,
            "project":          dict,
            "pipeline_detail":  list of {participant, entry, insights},
            "status_counts":    dict,
            "completed_count":  int,
            "still_needed":     int or None,
            "error":            str
        }
    """
    projects     = _load_projects()
    participants = _load_participants()

    project = _find_project(project_id, projects)
    if not project:
        return {"success": False, "error": f"Project '{project_id}' not found."}

    pipeline = project.get("participant_pipeline", [])
    target   = project.get("target_participants")

    status_counts = {}
    for entry in pipeline:
        s = entry.get("status", "")
        status_counts[s] = status_counts.get(s, 0) + 1

    completed_count = status_counts.get("completed", 0)

    pipeline_detail = []
    today = date.today()

    for entry in pipeline:
        participant = next(
            (p for p in participants if p["id"] == entry["participant_id"]), None
        )
        if not participant:
            continue

        # Days since the pipeline entry was created
        days_since = None
        if entry.get("date_added"):
            days_since = (today - datetime.strptime(entry["date_added"], "%Y-%m-%d").date()).days

        # Session insights for this specific project
        proj_insights = next(
            (s for s in participant.get("session_insights", [])
             if s["project_id"] == project_id),
            None
        )

        pipeline_detail.append({
            "participant": {
                "id":       participant["id"],
                "name":     participant["name"],
                "job_role": participant["job_role"],
            },
            "status":        entry["status"],
            "days_since":    days_since,
            "insights":      proj_insights,  # None if no notes yet
        })

    return {
        "success":         True,
        "project":         project,
        "pipeline_detail": pipeline_detail,
        "status_counts":   status_counts,
        "completed_count": completed_count,
        "still_needed":    (target - completed_count) if target else None,
    }


# ─────────────────────────────────────────────
# Organisations
# ─────────────────────────────────────────────

def get_all_organisations() -> list:
    """
    Returns all organisations, each with a computed 'participant_count' field.
    """
    organisations = _load_organisations()
    participants  = _load_participants()

    for org in organisations:
        org["participant_count"] = sum(
            1 for p in participants if p.get("organisation_id") == org["id"]
        )

    return organisations


def get_organisation_by_id(query: str) -> Optional[dict]:
    """
    Fetch an organisation by ID or name, with linked participants attached.

    Returns the org dict with a 'linked_participants' list, or None.
    """
    organisations = _load_organisations()
    participants  = _load_participants()

    org = _find_organisation(query, organisations)
    if not org:
        return None

    linked = [
        {
            "id":       p["id"],
            "name":     p["name"],
            "job_role": p["job_role"],
            "seniority_level": p["seniority_level"],
            "status":   p["status"],
            "sessions": len(p.get("participation_history", [])),
        }
        for p in participants if p.get("organisation_id") == org["id"]
    ]

    return {**org, "linked_participants": linked}


def add_organisation(
    name: str,
    sector: str,
    size: str,
    website: str = "",
    notes: str   = ""
) -> dict:
    """
    Add a new organisation to the directory.

    Returns:
        {
            "success": bool,
            "org_id":  str,
            "org":     dict,
            "error":   str
        }
    """
    organisations = _load_organisations()

    for org in organisations:
        if org["name"].lower() == name.lower():
            return {
                "success": False,
                "error":   f"An organisation named '{name}' already exists (ID: {org['id']})."
            }

    valid_sizes = {"startup", "sme", "enterprise", "micro-business", "scale-up", "sole trader"}
    if size.lower() not in valid_sizes:
        return {
            "success": False,
            "error":   f"Invalid size '{size}'. Use: startup, SME, scale-up, enterprise, micro-business, or sole trader."
        }

    new_org = {
        "id":         _generate_org_id(organisations),
        "name":       name,
        "sector":     sector,
        "size":       size.lower(),
        "website":    website,
        "notes":      notes,
        "date_added": str(date.today()),
    }

    organisations.append(new_org)
    _save_organisations(organisations)

    return {"success": True, "org_id": new_org["id"], "org": new_org}


# ─────────────────────────────────────────────
# Session notes
# ─────────────────────────────────────────────

def save_raw_notes(
    participant_id: str,
    project_id: str,
    raw_notes: str
) -> dict:
    """
    Save raw session notes to a participant's profile.
    Creates the session_insights entry if it doesn't exist yet.

    Returns:
        {
            "success":     bool,
            "participant": dict,  # updated profile
            "project":     dict,
            "raw_notes":   str,   # echoed back for the AI layer to process
            "error":       str
        }
    """
    participants = _load_participants()
    projects     = _load_projects()

    participant = _find_participant(participant_id, participants)
    project     = _find_project(project_id, projects)

    if not participant:
        return {"success": False, "error": f"No participant found matching '{participant_id}'."}
    if not project:
        return {"success": False, "error": f"Project '{project_id}' not found."}

    if "session_insights" not in participant:
        participant["session_insights"] = []

    existing = next(
        (s for s in participant["session_insights"] if s["project_id"] == project_id), None
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
            "quotes":          [],
        })

    _save_participants(participants)

    return {
        "success":     True,
        "participant": participant,
        "project":     project,
        "raw_notes":   raw_notes,
    }


def save_session_summary(
    participant_id: str,
    project_id: str,
    key_insights: list,
    follow_up_items: list,
    quotes: list = None
) -> dict:
    """
    Save structured insight extraction back to the participant's profile.
    Must be called after save_raw_notes.

    Returns:
        {
            "success":        bool,
            "participant":    dict,
            "insight_counts": dict,   # {"insights": n, "follow_ups": n, "quotes": n}
            "error":          str
        }
    """
    participants = _load_participants()
    participant  = _find_participant(participant_id, participants)

    if not participant:
        return {"success": False, "error": f"No participant found matching '{participant_id}'."}

    insights_list = participant.get("session_insights", [])
    entry         = next((s for s in insights_list if s["project_id"] == project_id), None)

    if not entry:
        return {
            "success": False,
            "error":   f"No raw notes found for project '{project_id}'. Call save_raw_notes first."
        }

    quotes = quotes or []

    entry["key_insights"]    = key_insights
    entry["follow_up_items"] = follow_up_items
    entry["quotes"]          = quotes

    _save_participants(participants)

    return {
        "success":     True,
        "participant": participant,
        "insight_counts": {
            "insights":   len(key_insights),
            "follow_ups": len(follow_up_items),
            "quotes":     len(quotes),
        },
    }


def get_all_session_insights(participant_id: str) -> dict:
    """
    Return all stored session insights for a participant across all projects.

    Returns:
        {
            "success":        bool,
            "participant":    dict,
            "session_insights": list,  # full insight entries, filtered to those with content
            "error":          str
        }
    """
    participants = _load_participants()
    participant  = _find_participant(participant_id, participants)

    if not participant:
        return {"success": False, "error": f"No participant found matching '{participant_id}'."}

    insights = [
        s for s in participant.get("session_insights", [])
        if s.get("key_insights")  # only entries that have been summarised
    ]

    return {
        "success":          True,
        "participant":      participant,
        "session_insights": insights,
    }


# ─────────────────────────────────────────────
# Email sending (Resend — external API, no AI)
# ─────────────────────────────────────────────

def send_email_via_resend(
    participant_id: str,
    project_id: str,
    subject: str,
    body: str
) -> dict:
    """
    Send an outreach email via Resend, then update the participant's
    pipeline status to 'invited' and record the touchpoint.

    Returns:
        {
            "success":          bool,
            "recipient_email":  str,
            "recipient_name":   str,
            "subject":          str,
            "error":            str
        }
    """
    import resend
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BASE_DIR, ".env.local"))

    api_key    = os.getenv("RESEND_API_KEY",     "")
    from_email = os.getenv("RESEND_FROM_EMAIL", "onboarding@resend.dev")

    if not api_key:
        return {
            "success": False,
            "error":   "RESEND_API_KEY is not set. Add it to .env.local."
        }

    participants = _load_participants()
    projects     = _load_projects()

    participant = _find_participant(participant_id, participants)
    project     = _find_project(project_id, projects)

    if not participant:
        return {"success": False, "error": f"Participant '{participant_id}' not found."}
    if not project:
        return {"success": False, "error": f"Project '{project_id}' not found."}

    to_email = participant["email"]

    html_body = "".join(
        f"<p>{line}</p>" if line.strip() else "<br>"
        for line in body.splitlines()
    )

    try:
        resend.api_key = api_key
        resend.Emails.send({
            "from":     from_email,
            "to":       [to_email],
            "subject":  subject,
            "html":     html_body,
            "reply_to": from_email,
        })
    except Exception as e:
        return {"success": False, "error": f"Resend API error: {str(e)}"}

    # Update participant record and pipeline on success
    today = str(date.today())
    participant["last_touchpoint"]      = "email"
    participant["last_touchpoint_date"] = today

    pipeline = project.get("participant_pipeline", [])
    entry    = next((e for e in pipeline if e["participant_id"] == participant["id"]), None)
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

    return {
        "success":         True,
        "recipient_email": to_email,
        "recipient_name":  participant["name"],
        "subject":         subject,
    }


# ─────────────────────────────────────────────
# CSV import
# ─────────────────────────────────────────────

def import_participants_from_csv(file_path: str) -> dict:
    """
    Read a CSV file and bulk-add participants to the panel.

    Returns:
        {
            "success": bool,
            "added":   list of str,   # names successfully added
            "skipped": list of str,   # names skipped (already in panel)
            "errors":  list of str,   # row-level error messages
        }
    """
    if not os.path.isabs(file_path):
        file_path = os.path.join(BASE_DIR, file_path)

    if not os.path.exists(file_path):
        return {
            "success": False,
            "added":   [],
            "skipped": [],
            "errors":  [f"File not found: '{file_path}'."],
        }

    required_columns = {
        "name", "email", "job_role", "seniority_level", "preferred_methods", "availability"
    }

    added   = []
    skipped = []
    errors  = []

    try:
        with open(file_path, "r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)

            fieldnames_lower = {col.strip().lower() for col in (reader.fieldnames or [])}
            missing = required_columns - fieldnames_lower
            if missing:
                return {
                    "success": False,
                    "added":   [],
                    "skipped": [],
                    "errors":  [f"Missing required columns: {', '.join(sorted(missing))}."],
                }

            for i, row in enumerate(reader, start=2):
                row  = {k: (v.strip() if v else "") for k, v in row.items()}
                name = row.get("name",  "")
                email = row.get("email", "")

                if not name or not email:
                    errors.append(f"Row {i}: missing name or email — skipped")
                    continue

                methods_raw = row.get("preferred_methods", "")
                methods     = [m.strip() for m in methods_raw.split(",") if m.strip()]

                result = add_participant(
                    name              = name,
                    email             = email,
                    job_role          = row.get("job_role",        ""),
                    seniority_level   = row.get("seniority_level", ""),
                    preferred_methods = methods,
                    availability      = row.get("availability",    ""),
                    persona           = row.get("persona",         ""),
                    organisation      = row.get("organisation",    ""),
                    notes             = row.get("notes",           ""),
                )

                if result["success"]:
                    added.append(name)
                elif "already exists" in result.get("error", ""):
                    skipped.append(name)
                else:
                    errors.append(f"Row {i} ({name}): {result.get('error', 'unknown error')}")

    except Exception as e:
        return {
            "success": False,
            "added":   added,
            "skipped": skipped,
            "errors":  errors + [f"File read error: {str(e)}"],
        }

    return {
        "success": True,
        "added":   added,
        "skipped": skipped,
        "errors":  errors,
    }
