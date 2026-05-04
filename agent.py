# agent.py
#
# 💡 ROLE IN THE REFACTORED ARCHITECTURE:
#    This file is the orchestration layer. It decides WHICH tools to call
#    based on natural language, runs them, and presents results to the user.
#
#    It no longer does any AI reasoning about research content — that has
#    moved into tools_ai.py. Claude here acts as a router and communicator:
#
#      User message
#        → Claude picks the right tool(s)
#          → tool runs (data op via tools_data, or AI op via tools_ai)
#            → result returned as structured string
#              → Claude presents it clearly to the researcher
#
# 💡 TWO WAYS TO USE THIS AGENT:
#
#    run_agent("your message")     → single-turn, no memory between calls
#                                    good for one-off tasks
#
#    session = ChatSession()       → multi-turn, remembers the whole conversation
#    session.chat("your message")    good for follow-up requests and context-heavy tasks

import os

import anthropic
from dotenv import load_dotenv
from tools import TOOLS, run_tool

load_dotenv(os.path.join(os.path.dirname(__file__), ".env.local"), override=True)
client = anthropic.Anthropic()

SYSTEM_PROMPT = """You are a helpful user research panel manager assistant.
You help researchers manage their participant panel: adding participants, tracking projects,
screening candidates, drafting outreach, and capturing session insights.

Guidelines:
- When adding or updating participants, confirm clearly what was saved.
- When screening: the tool ranks participants by AI fit score — present the top candidates
  and offer to add them to the project pipeline with add_to_pipeline.
- When drafting emails: the tool writes the email — present the subject and body for the
  researcher to review, then offer to send it with send_outreach_email.
- When extracting session insights: the tool handles extraction automatically — present
  the insights and highlight any important follow-up items.
- Always be concise and friendly."""


# ─────────────────────────────────────────────
# Core agent loop (shared by both run_agent and ChatSession)
# ─────────────────────────────────────────────

def _agent_loop(messages: list, verbose: bool) -> tuple:
    """
    The core back-and-forth between your code and Claude.

    💡 This is now a private helper (note the _ prefix — Python convention
       for "internal use only"). Both run_agent and ChatSession use it,
       so we only have to write the loop logic once.

    Returns: (answer, final_messages)
       answer         — Claude's text response
       final_messages — the full conversation including this exchange,
                        ready to be passed into the next call
    """
    while True:
        response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages
        )

        if response.stop_reason == "end_turn":
            for block in response.content:
                if block.type == "text":
                    # Return the answer AND the updated conversation history
                    final_messages = messages + [{"role": "assistant", "content": response.content}]
                    return block.text, final_messages

        elif response.stop_reason == "tool_use":
            messages = messages + [{"role": "assistant", "content": response.content}]

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    if verbose:
                        print(f"  → Claude calls: {block.name}({block.input})")

                    result = run_tool(block.name, block.input)

                    if verbose:
                        print(f"  ← Result: {result}")

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

            messages = messages + [{"role": "user", "content": tool_results}]

        else:
            return f"Unexpected stop reason: {response.stop_reason}", messages


# ─────────────────────────────────────────────
# run_agent — single-turn (no memory)
# ─────────────────────────────────────────────

def run_agent(user_message: str, verbose: bool = True) -> str:
    """
    Single-turn agent call. Each call starts fresh with no memory.

    💡 WHEN TO USE:
       Discrete, self-contained tasks that don't need context:
       - "Add this participant..."
       - "Screen PRJ-001"
       - "Show me everyone in the panel"

    All your existing cells use this — nothing changes for them.
    """
    answer, _ = _agent_loop(
        [{"role": "user", "content": user_message}],
        verbose
    )
    return answer


# ─────────────────────────────────────────────
# ChatSession — multi-turn (with memory)
# ─────────────────────────────────────────────

class ChatSession:
    """
    Multi-turn conversation — Claude remembers everything said earlier.

    💡 HOW MEMORY WORKS:
       self.history is a list that grows with every exchange.
       Before each call, we prepend it to the new message so Claude
       sees the full conversation thread — like replying in an email chain
       instead of sending a new email each time.

       Call 1:  history = []
                messages sent → [user: "I need 2 more participants..."]
                history after → [user: "...", assistant: "..."]

       Call 2:  history = [user: "...", assistant: "..."]
                messages sent → [user: "...", assistant: "...", user: "Shortlist Priya"]
                history after → [user: "...", assistant: "...", user: "...", assistant: "..."]

       Claude now sees the full thread every time.

    💡 WHEN TO USE:
       Follow-up requests and multi-step conversations:
       - "Shortlist Priya" (after Claude already recommended her)
       - "Now draft emails for both of them"
       - "Actually, skip Maya — just Priya"

    Usage:
        # Full history (default — good for short sessions)
        session = ChatSession()

        # Trimmed history (good for long sessions / production)
        session = ChatSession(max_turns=5)

        session.chat("I need 2 more participants for the Checkout Flow project")
        session.chat("Shortlist Priya and draft emails for both her and Maya")
        session.reset()  # start a fresh conversation
    """

    def __init__(self, verbose: bool = True, max_turns: int = None):
        """
        Parameters:
            verbose   — print tool calls as they happen (default True)
            max_turns — how many back-and-forth exchanges to keep in memory.
                        None = keep everything (default, good for short sessions)
                        5    = keep last 5 exchanges (good for production)

        💡 WHAT IS A "TURN"?
           One turn = you say something + Claude responds.
           With max_turns=5, Claude remembers the last 5 exchanges
           and forgets anything older.

           Think of it like a sliding window:

           Turn 1: [you: "screen PRJ-001", claude: "shortlisted Sarah..."]  ← oldest, dropped at turn 6
           Turn 2: [you: "draft email for Sarah", claude: "here's the email"]
           Turn 3: [you: "also draft for Maya", claude: "here's Maya's email"]
           Turn 4: [you: "mark Sarah as invited", claude: "done!"]
           Turn 5: [you: "show me PRJ-001", claude: "here's the project"]  ← most recent, always kept
        """
        self.history  = []
        self.verbose  = verbose
        self.max_turns = max_turns

    def _trim_history(self):
        """
        Trims history to the last max_turns exchanges.

        💡 WHY * 2?
           Each turn produces at least 2 messages in the list:
             - 1 user message
             - 1 assistant response
           Tool calls add more (tool_use + tool_result), so trimming
           by messages (not turns) is an approximation — but a good
           enough one for cost management.
        """
        if self.max_turns is None:
            return  # no trimming — keep full history

        keep = self.max_turns * 2
        if len(self.history) > keep:
            self.history = self.history[-keep:]

    def chat(self, message: str) -> str:
        """Send a message. Claude remembers up to max_turns exchanges."""
        self._trim_history()   # trim BEFORE sending, so we stay within budget
        messages = self.history + [{"role": "user", "content": message}]
        answer, self.history = _agent_loop(messages, self.verbose)
        return answer

    def reset(self):
        """Clear the conversation and start fresh."""
        self.history = []
        print("✅ Session cleared — starting fresh.")
