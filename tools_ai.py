# tools_ai.py — AI operations layer
#
# 💡 WHAT THIS FILE IS FOR:
#    This is the AI layer of the refactored architecture.
#    Every function here uses Claude for reasoning and returns structured data.
#
#    Rules this file must always follow:
#      ✅ Imports data from tools_data.py — never reads JSON files directly
#      ✅ Returns structured dicts (not conversational strings)
#      ✅ Each function makes exactly one Claude API call
#      ✅ Uses "forced tool use" to guarantee structured output
#
# 💡 THE KEY PATTERN — FORCED TOOL USE:
#    In the normal agent loop, Claude *chooses* which tool to call.
#    Here we flip it: we define a schema for what we want back,
#    then force Claude to "call" that schema as if it were a tool.
#    Claude fills in the fields → we read block.input as structured data.
#
#    Normal agent loop:  Claude → picks tool → gets data → answers in text
#    This file:          We send prompt → Claude fills schema → we read block.input
#
#    This is more reliable than asking Claude to "reply in JSON" because
#    Claude is trained to fill tool schemas accurately.
#
# 💡 WHY IMPORT FROM tools_data.py?
#    The AI layer should never know about JSON files.
#    It asks the data layer for what it needs, reasons over it,
#    then hands structured results back to whoever called it.
#    Clear boundary → easy to test, easy to swap either layer later.

import os

import anthropic
from dotenv import load_dotenv

from tools_data import (
    add_participant_to_pipeline,
    get_all_session_insights,
    get_project_data_for_email,
    get_project_data_for_screening,
    get_project_data_for_summary,
    save_raw_notes,
    save_session_summary,
)

load_dotenv(os.path.join(os.path.dirname(__file__), ".env.local"), override=True)

# ─────────────────────────────────────────────
# Claude client — shared across all functions
# ─────────────────────────────────────────────

MODEL  = "claude-opus-4-5"   # change here to update all AI functions at once
client = anthropic.Anthropic()


# ─────────────────────────────────────────────
# Private helper — the forced tool use call
# ─────────────────────────────────────────────

def _call_claude_for_structured_output(
    prompt: str,
    output_schema: dict,
    system: str  = "",
    max_tokens: int = 1024
) -> dict:
    """
    Send a prompt to Claude and force it to respond using a specific schema.

    💡 HOW IT WORKS:
       1. We wrap the desired schema in a fake "tool" definition
       2. We set tool_choice to force Claude to call exactly that tool
       3. Claude fills in the schema fields (like a form)
       4. We extract block.input — that's our structured response

    Args:
        prompt:        The user-facing prompt Claude should respond to
        output_schema: A JSON Schema dict describing the fields we want back
        system:        Optional system prompt
        max_tokens:    Token budget for Claude's response

    Returns:
        The structured dict from block.input, or {"error": str} on failure.
    """
    # Wrap the schema in a tool definition
    # 💡 The tool name is arbitrary — it's just a hook for the forced call
    output_tool = {
        "name":        "submit_result",
        "description": "Submit the structured result.",
        "input_schema": output_schema,
    }

    messages = [{"role": "user", "content": prompt}]

    try:
        response = client.messages.create(
            model      = MODEL,
            max_tokens = max_tokens,
            system     = system,
            tools      = [output_tool],
            tool_choice = {"type": "tool", "name": "submit_result"},
            messages   = messages,
        )

        for block in response.content:
            if block.type == "tool_use":
                return block.input  # ← the structured data Claude filled in

        return {"error": "Claude did not return a tool_use block."}

    except Exception as e:
        return {"error": f"Claude API error: {str(e)}"}


# ─────────────────────────────────────────────
# 1. Screen participants
# ─────────────────────────────────────────────

def screen_participants_with_ai(project_id: str) -> dict:
    """
    Use Claude to screen and rank all active participants against a project's
    criteria. Returns a ranked list with fit scores and reasoning.

    💡 WHAT CHANGED vs. the old screen_participants tool:
       Before: tool returned a formatted text blob → Claude reasoned in the agent loop
       Now:    this function calls Claude directly → returns a structured ranking
       The intelligence is now self-contained here, not spread across the agent loop.

    Args:
        project_id: e.g. "PRJ-001"

    Returns:
        {
            "success":             bool,
            "project_id":          str,
            "project_name":        str,
            "ranked_participants": [
                {
                    "participant_id": str,
                    "name":          str,
                    "fit_score":     float,   # 0.0 (poor fit) → 1.0 (perfect fit)
                    "reasoning":     str,     # plain-language explanation
                    "strengths":     list,    # what makes them a good fit
                    "concerns":      list     # anything that reduces fit
                },
                ...                           # ordered best → worst fit
            ],
            "total_screened":      int,
            "error":               str        # present on failure
        }
    """
    # 1. Fetch data from the data layer
    data = get_project_data_for_screening(project_id)
    if not data["success"]:
        return {"success": False, "error": data["error"]}

    project    = data["project"]
    candidates = data["candidates"]

    if not candidates:
        return {
            "success":             False,
            "error":               "No active participants in the panel to screen."
        }

    # 2. Build the prompt
    sc = project.get("screening_criteria", {})
    criteria_lines = []
    if sc.get("job_role"):        criteria_lines.append(f"- Role: {sc['job_role']}")
    if sc.get("seniority_level"): criteria_lines.append(f"- Seniority: {sc['seniority_level']}")
    if sc.get("methods"):         criteria_lines.append(f"- Methods: {', '.join(sc['methods'])}")
    if sc.get("availability"):    criteria_lines.append(f"- Availability: {sc['availability']}")
    if sc.get("persona"):         criteria_lines.append(f"- Persona: {sc['persona']}")
    criteria_text = "\n".join(criteria_lines) if criteria_lines else "No specific criteria set."

    candidate_lines = []
    for p in candidates:
        methods  = ", ".join(p["preferred_methods"]) if p["preferred_methods"] else "none"
        sessions = len(p["participation_history"])
        candidate_lines.append(
            f"ID: {p['id']} | Name: {p['name']} | Role: {p['job_role']} | "
            f"Seniority: {p['seniority_level']} | Methods: {methods} | "
            f"Availability: {p['availability']} | Sessions completed: {sessions} | "
            f"Persona: {p.get('persona') or 'not set'}"
        )
    candidates_text = "\n".join(candidate_lines)

    prompt = f"""You are a user research ops specialist. Screen these participants for the following study.

PROJECT: {project['project_name']}
GOAL: {project['research_goal']}

SCREENING CRITERIA:
{criteria_text}

PARTICIPANTS TO SCREEN:
{candidates_text}

Assess every participant against the criteria. Assign a fit_score from 0.0 (poor fit) to 1.0 (perfect fit).
Return ALL participants, ordered from best to worst fit. Include even poor fits so the researcher has the full picture."""

    # 3. Define the output schema Claude must fill
    output_schema = {
        "type": "object",
        "properties": {
            "ranked_participants": {
                "type": "array",
                "description": "All participants ranked from best fit to worst fit.",
                "items": {
                    "type": "object",
                    "properties": {
                        "participant_id": {
                            "type": "string",
                            "description": "The participant's ID, e.g. P001"
                        },
                        "name": {
                            "type": "string",
                            "description": "The participant's full name"
                        },
                        "fit_score": {
                            "type": "number",
                            "description": "Fit score from 0.0 (no fit) to 1.0 (perfect fit)"
                        },
                        "reasoning": {
                            "type": "string",
                            "description": "One or two sentences explaining the score"
                        },
                        "strengths": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "What makes this participant a good fit"
                        },
                        "concerns": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "What reduces their fit — empty list if none"
                        },
                    },
                    "required": ["participant_id", "name", "fit_score", "reasoning", "strengths", "concerns"]
                }
            }
        },
        "required": ["ranked_participants"]
    }

    # 4. Call Claude
    result = _call_claude_for_structured_output(
        prompt        = prompt,
        output_schema = output_schema,
        max_tokens    = 2048,
    )

    if "error" in result:
        return {"success": False, "error": result["error"]}

    return {
        "success":             True,
        "project_id":          project["id"],
        "project_name":        project["project_name"],
        "ranked_participants": result.get("ranked_participants", []),
        "total_screened":      len(candidates),
    }


# ─────────────────────────────────────────────
# 2. Draft outreach email
# ─────────────────────────────────────────────

def draft_email_with_ai(participant_id: str, project_id: str) -> dict:
    """
    Use Claude to draft a personalised outreach email for a participant.
    Automatically incorporates past session context if it exists.

    💡 WHAT CHANGED vs. the old draft_outreach_email tool:
       Before: tool returned context text → Claude wrote the email in the agent loop
       Now:    this function calls Claude → returns subject + body as structured fields
       The email is now a discrete, testable output — not buried in a conversation turn.

    Args:
        participant_id: e.g. "P003" or "Anika Patel"
        project_id:     e.g. "PRJ-001"

    Returns:
        {
            "success":               bool,
            "subject":               str,
            "body":                  str,
            "recipient_email":       str,
            "recipient_name":        str,
            "personalisation_used":  list,  # what context was woven into the email
            "error":                 str    # present on failure
        }
    """
    # 1. Fetch data from the data layer
    data = get_project_data_for_email(project_id, participant_id)
    if not data["success"]:
        return {"success": False, "error": data["error"]}

    participant  = data["participant"]
    project      = data["project"]
    past_context = data["past_context"]

    # 2. Build the prompt
    methods     = ", ".join(participant["preferred_methods"]) if participant["preferred_methods"] else "not specified"
    sessions    = len(participant["participation_history"])
    sc          = project.get("screening_criteria", {})
    study_method = ", ".join(sc.get("methods", [])) if sc.get("methods") else "research session"

    past_context_text = ""
    personalisation_sources = []

    if past_context["follow_up_items"] or past_context["quotes"]:
        personalisation_sources.append("past_session_context")
        lines = ["\nPAST SESSION CONTEXT — weave this naturally into the email:"]
        if past_context["follow_up_items"]:
            lines.append("Follow-up items from previous sessions:")
            for item in past_context["follow_up_items"]:
                lines.append(f"  → {item}")
        if past_context["quotes"]:
            lines.append("Things they said previously:")
            for quote in past_context["quotes"]:
                lines.append(f'  "{quote}"')
        past_context_text = "\n".join(lines)

    prompt = f"""You are a user research ops specialist. Draft a warm, personalised outreach email.

PARTICIPANT
Name: {participant['name']}
Role: {participant['job_role']} ({participant['seniority_level']})
Organisation: {participant.get('organisation') or 'not specified'}
Preferred methods: {methods}
Availability: {participant['availability']}
Past sessions with us: {sessions}
Notes: {participant.get('notes') or 'none'}

PROJECT
Name: {project['project_name']}
Goal: {project['research_goal']}
Session type: {study_method}
{past_context_text}

Write a warm, concise email (3–4 short paragraphs). Reference their actual role and the real research goal.
Do not use a generic template tone. End with a clear call to action."""

    # 3. Define the output schema
    output_schema = {
        "type": "object",
        "properties": {
            "subject": {
                "type": "string",
                "description": "Email subject line — specific and personal, not generic"
            },
            "body": {
                "type": "string",
                "description": "Full plain-text email body, 3-4 short paragraphs"
            },
            "personalisation_used": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Short list of what was personalised, e.g. ['referenced job role', 'mentioned past session quote']"
            },
        },
        "required": ["subject", "body", "personalisation_used"]
    }

    # 4. Call Claude
    result = _call_claude_for_structured_output(
        prompt        = prompt,
        output_schema = output_schema,
        max_tokens    = 1024,
    )

    if "error" in result:
        return {"success": False, "error": result["error"]}

    # Add participant data as source of personalisation if used
    if sessions > 0:
        personalisation_sources.append("participation_history")

    used = result.get("personalisation_used", []) + personalisation_sources

    return {
        "success":              True,
        "subject":              result.get("subject", ""),
        "body":                 result.get("body", ""),
        "recipient_email":      participant["email"],
        "recipient_name":       participant["name"],
        "personalisation_used": used,
    }


# ─────────────────────────────────────────────
# 3. Extract session insights
# ─────────────────────────────────────────────

def extract_session_insights(
    participant_id: str,
    project_id: str,
    raw_notes: str
) -> dict:
    """
    Save raw session notes and use Claude to extract structured insights.
    Combines what was previously two separate tool calls
    (add_session_notes → Claude reads → save_session_summary).

    💡 WHAT CHANGED vs. the old two-step pattern:
       Before: add_session_notes saved notes → agent loop prompted Claude
               → Claude called save_session_summary
       Now:    this single function does all three steps atomically.
       Much cleaner for MCP — one call, one result, nothing split across turns.

    Args:
        participant_id: e.g. "P003" or "Anika Patel"
        project_id:     e.g. "PRJ-001"
        raw_notes:      Messy raw notes from the session (any format)

    Returns:
        {
            "success":          bool,
            "participant_name": str,
            "project_name":     str,
            "key_insights":     list,
            "follow_up_items":  list,
            "quotes":           list,
            "error":            str    # present on failure
        }
    """
    # 1. Save the raw notes to the data layer first
    save_result = save_raw_notes(participant_id, project_id, raw_notes)
    if not save_result["success"]:
        return {"success": False, "error": save_result["error"]}

    participant  = save_result["participant"]
    project      = save_result["project"]

    # 2. Build the prompt
    prompt = f"""You are a skilled user researcher. Extract structured insights from these raw session notes.

PARTICIPANT: {participant['name']} ({participant['job_role']})
PROJECT: {project['project_name']}
GOAL: {project['research_goal']}

RAW NOTES:
{'─' * 40}
{raw_notes}
{'─' * 40}

Extract:
- 2-5 key insights (what did you learn? what patterns emerged?)
- Follow-up items (specific things to explore or action next time)
- Notable direct quotes (only if clearly stated — exact words, not paraphrased)

Be precise and specific. Avoid vague statements like "user was frustrated" —
say what specifically frustrated them and why."""

    # 3. Define the output schema
    output_schema = {
        "type": "object",
        "properties": {
            "key_insights": {
                "type": "array",
                "items": {"type": "string"},
                "description": "2-5 specific, actionable research insights from this session"
            },
            "follow_up_items": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Specific things to follow up on in the next interaction with this participant"
            },
            "quotes": {
                "type": "array",
                "items": {"type": "string"},
                "description": "1-3 notable direct quotes. Only include if clearly stated verbatim. Empty list if none."
            },
        },
        "required": ["key_insights", "follow_up_items", "quotes"]
    }

    # 4. Call Claude
    result = _call_claude_for_structured_output(
        prompt        = prompt,
        output_schema = output_schema,
        max_tokens    = 1024,
    )

    if "error" in result:
        return {"success": False, "error": result["error"]}

    key_insights    = result.get("key_insights",    [])
    follow_up_items = result.get("follow_up_items", [])
    quotes          = result.get("quotes",          [])

    # 5. Save the structured summary back to the data layer
    summary_result = save_session_summary(
        participant_id  = participant["id"],
        project_id      = project_id,
        key_insights    = key_insights,
        follow_up_items = follow_up_items,
        quotes          = quotes,
    )

    if not summary_result["success"]:
        return {"success": False, "error": summary_result["error"]}

    return {
        "success":          True,
        "participant_name": participant["name"],
        "project_name":     project["project_name"],
        "key_insights":     key_insights,
        "follow_up_items":  follow_up_items,
        "quotes":           quotes,
    }


# ─────────────────────────────────────────────
# 4. Summarise project status
# ─────────────────────────────────────────────

def summarise_project_with_ai(project_id: str) -> dict:
    """
    Use Claude to generate a plain-language project status summary,
    based on pipeline data and collected session insights.

    💡 WHAT CHANGED vs. the old get_project_summary tool:
       Before: tool returned a data blob ending with "Please give a concise status update..."
               → Claude responded in the agent loop
       Now:    this function calls Claude → returns structured summary fields
       The AI output is now a predictable structure, not a free-form response.

    Args:
        project_id: e.g. "PRJ-001"

    Returns:
        {
            "success":                  bool,
            "project_id":               str,
            "project_name":             str,
            "status_summary":           str,   # plain-language paragraph
            "key_observations":         list,  # bullet-point findings from sessions
            "recommended_next_action":  str,   # single most important next step
            "data": {                          # raw stats for reference
                "completed_count":  int,
                "still_needed":     int,
                "status_counts":    dict,
            },
            "error": str                       # present on failure
        }
    """
    # 1. Fetch data from the data layer
    data = get_project_data_for_summary(project_id)
    if not data["success"]:
        return {"success": False, "error": data["error"]}

    project         = data["project"]
    pipeline_detail = data["pipeline_detail"]
    status_counts   = data["status_counts"]
    completed_count = data["completed_count"]
    still_needed    = data["still_needed"]

    # 2. Build the prompt
    target = project.get("target_participants", "unknown")
    pct    = f"{int(completed_count / target * 100)}%" if isinstance(target, int) and target > 0 else "n/a"

    pipeline_lines = []
    for item in pipeline_detail:
        p         = item["participant"]
        days_text = f" ({item['days_since']}d ago)" if item["days_since"] is not None else ""
        pipeline_lines.append(
            f"  • {p['name']} ({p['id']}) — {item['status']}{days_text}"
        )

    insights_lines = []
    for item in pipeline_detail:
        if item["status"] == "completed" and item["insights"]:
            ins = item["insights"]
            if ins.get("key_insights"):
                insights_lines.append(f"\n  From {item['participant']['name']}:")
                for insight in ins["key_insights"]:
                    insights_lines.append(f"    • {insight}")
                for quote in ins.get("quotes", []):
                    insights_lines.append(f'    "{quote}"')

    prompt = f"""You are a user research ops specialist. Write a concise project status update.

PROJECT: {project['project_name']}
GOAL:    {project['research_goal']}
STATUS:  {project['project_status']}

PROGRESS
Completed: {completed_count} / {target} ({pct})
Still needed: {still_needed}
Shortlisted: {status_counts.get('shortlisted', 0)}
Invited:     {status_counts.get('invited', 0)}
Confirmed:   {status_counts.get('confirmed', 0)}
Declined:    {status_counts.get('declined', 0)}

PIPELINE
{chr(10).join(pipeline_lines) if pipeline_lines else '  No participants yet.'}
{'INSIGHTS COLLECTED SO FAR' + chr(10) + chr(10).join(insights_lines) if insights_lines else ''}

Write a plain-language status update a non-technical researcher would find useful.
Highlight anything that needs attention. Suggest the single most important next action."""

    # 3. Define the output schema
    output_schema = {
        "type": "object",
        "properties": {
            "status_summary": {
                "type": "string",
                "description": "1-2 sentence plain-language project status overview"
            },
            "key_observations": {
                "type": "array",
                "items": {"type": "string"},
                "description": "2-4 notable observations about the project's progress or session insights so far"
            },
            "recommended_next_action": {
                "type": "string",
                "description": "The single most important next action the researcher should take"
            },
        },
        "required": ["status_summary", "key_observations", "recommended_next_action"]
    }

    # 4. Call Claude
    result = _call_claude_for_structured_output(
        prompt        = prompt,
        output_schema = output_schema,
        max_tokens    = 1024,
    )

    if "error" in result:
        return {"success": False, "error": result["error"]}

    return {
        "success":                 True,
        "project_id":              project["id"],
        "project_name":            project["project_name"],
        "status_summary":          result.get("status_summary", ""),
        "key_observations":        result.get("key_observations", []),
        "recommended_next_action": result.get("recommended_next_action", ""),
        "data": {
            "completed_count": completed_count,
            "still_needed":    still_needed,
            "status_counts":   status_counts,
        },
    }
