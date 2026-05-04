# test_mcp_tools.py
#
# Integration test for all 6 MCP server tools.
# Runs against the real data files and the live Claude API.
#
# HOW TO RUN:
#   uv run test_mcp_tools.py
#
# WHAT IT TESTS:
#   - Each tool returns the expected shape
#   - Success/error handling works correctly
#   - AI tools produce meaningful structured output
#   - Any writes made during the test are cleaned up afterwards

import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

# Import the tools directly from mcp_server — same code Claude Desktop calls
from mcp_server import (
    add_participant_to_panel,
    check_participation_history,
    draft_outreach_email,
    extract_session_insights,
    get_participant_details,
    screen_participants,
)

# ─────────────────────────────────────────────
# Test runner helpers
# ─────────────────────────────────────────────

PASS = "✅"
FAIL = "❌"
results = []

def check(label: str, condition: bool, detail: str = ""):
    icon = PASS if condition else FAIL
    msg  = f"  {icon} {label}"
    if detail:
        msg += f"\n     {detail}"
    print(msg)
    results.append((label, condition))
    return condition


def section(title: str):
    print(f"\n{'─' * 50}")
    print(f"  {title}")
    print(f"{'─' * 50}")


def show(label: str, value):
    """Pretty-print a value for reference."""
    if isinstance(value, (dict, list)):
        formatted = json.dumps(value, indent=4, default=str)
        # Indent each line
        formatted = "\n".join("     " + l for l in formatted.splitlines())
        print(f"  📄 {label}:\n{formatted}")
    else:
        print(f"  📄 {label}: {value}")


# ─────────────────────────────────────────────
# Track new participant IDs so we can clean up
# ─────────────────────────────────────────────

added_participant_id = None


# ─────────────────────────────────────────────
# Tool 4: check_participation_history
# (pure data — run first, no API cost)
# ─────────────────────────────────────────────

section("Tool 4 — check_participation_history")

result = check_participation_history("P001")

check("Returns success=True for existing participant",
      result.get("success") is True)
check("Contains participant sub-dict",
      "participant" in result and "name" in result["participant"])
check("Contains history list",
      "history" in result and isinstance(result["history"], list))
check("Contains total count",
      "total" in result and isinstance(result["total"], int))

show("Sample output", {
    "success":     result["success"],
    "participant": result["participant"],
    "total":       result["total"],
    "first_entry": result["history"][0] if result["history"] else None,
})

# Error case
err_result = check_participation_history("nobody-xyz")
check("Returns success=False for unknown participant",
      err_result.get("success") is False)
check("Error result contains 'error' key",
      "error" in err_result)


# ─────────────────────────────────────────────
# Tool 6: get_participant_details
# (pure data)
# ─────────────────────────────────────────────

section("Tool 6 — get_participant_details")

result = get_participant_details("P001")

check("Returns success=True for known ID",
      result.get("success") is True)
check("Participant has expected fields",
      all(k in result["participant"] for k in ["id", "name", "email", "job_role", "status"]))
check("Name lookup works (partial name)",
      get_participant_details("Chloe").get("success") is True)
check("Returns success=False for unknown query",
      get_participant_details("zzz-nobody").get("success") is False)

show("Sample output", {
    "success": result["success"],
    "participant": {k: result["participant"][k]
                    for k in ["id", "name", "email", "job_role", "seniority_level", "status"]},
})


# ─────────────────────────────────────────────
# Tool 5: add_participant_to_panel
# (data write — we'll clean up afterwards)
# ─────────────────────────────────────────────

section("Tool 5 — add_participant_to_panel")

result = add_participant_to_panel(
    name="MCP Test Participant",
    email="mcp.test.temp@example.com",
    job_role="Product Manager",
    seniority_level="Senior",
    preferred_methods=["interview", "usability test"],
    availability="Weekday mornings",
    persona="Power User",
    notes="Added by test_mcp_tools.py — safe to delete",
)

check("Returns success=True",
      result.get("success") is True)
check("Returns a participant_id",
      "participant_id" in result and result["participant_id"].startswith("P"))
check("Returned participant has correct name",
      result.get("participant", {}).get("name") == "MCP Test Participant")

if result.get("success"):
    added_participant_id = result["participant_id"]

show("Sample output", {
    "success":        result["success"],
    "participant_id": result.get("participant_id"),
    "name":           result.get("participant", {}).get("name"),
    "email":          result.get("participant", {}).get("email"),
})

# Duplicate prevention
dup = add_participant_to_panel(
    name="MCP Test Participant",
    email="mcp.test.temp@example.com",
    job_role="Product Manager",
    seniority_level="Senior",
    preferred_methods=["interview"],
    availability="Mornings",
)
check("Duplicate email is rejected with success=False",
      dup.get("success") is False)


# ─────────────────────────────────────────────
# Tool 1: screen_participants   (AI call)
# ─────────────────────────────────────────────

section("Tool 1 — screen_participants  [AI]")

result = screen_participants("PRJ-001")

check("Returns success=True",
      result.get("success") is True)
check("Contains ranked_participants list",
      "ranked_participants" in result and isinstance(result["ranked_participants"], list))
check("Each entry has required fields",
      all(
          all(k in p for k in ["participant_id", "name", "fit_score", "reasoning", "strengths", "concerns"])
          for p in result.get("ranked_participants", [])
      ))
check("fit_score is between 0 and 1",
      all(0.0 <= p["fit_score"] <= 1.0 for p in result.get("ranked_participants", [])))
check("total_screened matches list length",
      result.get("total_screened") == len(result.get("ranked_participants", [])))

top3 = result.get("ranked_participants", [])[:3]
show("Top 3 results", [
    {"name": p["name"], "fit_score": p["fit_score"], "reasoning": p["reasoning"][:80] + "..."}
    for p in top3
])

# Error case
err = screen_participants("PRJ-999")
check("Returns success=False for unknown project",
      err.get("success") is False)


# ─────────────────────────────────────────────
# Tool 2: draft_outreach_email   (AI call)
# ─────────────────────────────────────────────

section("Tool 2 — draft_outreach_email  [AI]")

result = draft_outreach_email("P002", "PRJ-001")

check("Returns success=True",
      result.get("success") is True)
check("Contains subject string",
      "subject" in result and isinstance(result["subject"], str) and len(result["subject"]) > 5)
check("Contains body string",
      "body" in result and isinstance(result["body"], str) and len(result["body"]) > 50)
check("Contains recipient_email",
      "recipient_email" in result and "@" in result.get("recipient_email", ""))
check("Contains personalisation_used list",
      "personalisation_used" in result and isinstance(result["personalisation_used"], list))

show("Sample output", {
    "success":             result["success"],
    "recipient_name":      result.get("recipient_name"),
    "recipient_email":     result.get("recipient_email"),
    "subject":             result.get("subject"),
    "body_preview":        result.get("body", "")[:120] + "...",
    "personalisation_used": result.get("personalisation_used", [])[:3],
})

err = draft_outreach_email("P999", "PRJ-001")
check("Returns success=False for unknown participant",
      err.get("success") is False)


# ─────────────────────────────────────────────
# Tool 3: extract_session_insights   (AI call)
# ─────────────────────────────────────────────

section("Tool 3 — extract_session_insights  [AI]")

RAW_NOTES = """
mcp test session - noah jenkins - checkout flow project
~40 min session, ran a bit over

noah shops maybe 2-3x per month online, mostly electronics and hobby stuff
main friction: saved cards stop working after a while?? he has to re-enter them
also said he always checks if site has paypal before he adds to cart
if no paypal he usually doesn't bother unless it's something he really wants

interesting: he described the progress bar on checkout as "a loading bar for my money"
thought it was funny but actually said it helps him not abandon

he doesn't read return policies - just assumes big sites are fine
buys based on delivery speed, same/next day is a dealbreaker criteria for him

got distracted talking about his last bad experience - bought something,
no confirmation email came, thought it failed, bought again, ended up with 2
follow up on: does he want sms vs email confirmation?
and: would saved address/card across sessions change his behaviour?
"""

result = extract_session_insights("P006", "PRJ-001", RAW_NOTES)

check("Returns success=True",
      result.get("success") is True)
check("Contains participant_name",
      "participant_name" in result and len(result["participant_name"]) > 0)
check("Contains key_insights list (non-empty)",
      "key_insights" in result and len(result.get("key_insights", [])) > 0)
check("Contains follow_up_items list",
      "follow_up_items" in result and isinstance(result["follow_up_items"], list))
check("Contains quotes list",
      "quotes" in result and isinstance(result["quotes"], list))

show("Extracted insights", {
    "participant":    result.get("participant_name"),
    "key_insights":  result.get("key_insights", []),
    "follow_up_items": result.get("follow_up_items", []),
    "quotes":        result.get("quotes", []),
})


# ─────────────────────────────────────────────
# Cleanup — remove any participants added during testing
# ─────────────────────────────────────────────

section("Cleanup")

from tools_data import _load_participants, _save_participants

participants = _load_participants()
before = len(participants)
participants = [p for p in participants if p.get("email") != "mcp.test.temp@example.com"]
_save_participants(participants)
removed = before - len(participants)
check(f"Removed {removed} test participant(s) from panel",
      removed >= 1)


# ─────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────

print(f"\n{'═' * 50}")
passed = sum(1 for _, ok in results if ok)
failed = sum(1 for _, ok in results if not ok)
total  = len(results)

print(f"  Results: {passed}/{total} checks passed", end="")
if failed:
    print(f"  ({failed} failed)")
    print("\n  Failed checks:")
    for label, ok in results:
        if not ok:
            print(f"    {FAIL} {label}")
else:
    print("  — all good!")
print(f"{'═' * 50}\n")

sys.exit(0 if failed == 0 else 1)
