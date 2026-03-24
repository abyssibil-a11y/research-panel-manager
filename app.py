# app.py
#
# 💡 This file wraps your agent in a web chat interface using Gradio.
#
#    Run it with:  python3 app.py
#    Then open:   http://localhost:7860 in your browser
#
# HOW GRADIO WORKS (in one sentence):
#    You define Python functions, then connect them to UI elements
#    with .click() and .submit(). Gradio handles all the web stuff.
#
# NEW CONCEPT — gr.State:
#    Web apps can have multiple tabs/users at the same time.
#    gr.State stores a Python object *per browser tab*, so two
#    researchers using the app simultaneously don't share memory.
#    Think of it as a "per-user variable".

import gradio as gr
from agent import ChatSession
from tools import run_tool


# ─────────────────────────────────────────────
# Functions (the logic behind each UI action)
# ─────────────────────────────────────────────

def create_session() -> ChatSession:
    """Creates a fresh ChatSession for each new browser tab."""
    return ChatSession(verbose=False)  # verbose=False keeps the terminal clean


def respond(message: str, history: list, session: ChatSession):
    """
    Called every time the user sends a message.

    💡 Parameters come from the UI (inputs=[...] below):
         message  — what the user typed in the text box
         history  — the chat log Gradio is displaying
         session  — this tab's ChatSession (stored in gr.State)

    💡 Returns go back to the UI (outputs=[...] below):
         ""       — clears the text input after sending
         history  — updated chat log with the new exchange
         session  — same session object (its internal history has grown)
    """
    if not message.strip():
        return "", history, session

    bot_response = session.chat(message)

    # Gradio 4.x format: each item is a [user_message, bot_response] pair
    history.append([message, bot_response])

    return "", history, session


def clear_chat(session: ChatSession):
    """Clears the chat window and resets Claude's memory."""
    session.reset()
    return [], session


def import_csv(file) -> str:
    """
    Called when the researcher clicks Import in the CSV section.

    💡 HOW GRADIO FILE UPLOAD WORKS:
       gr.File gives us a file object with a .name attribute —
       that's the temporary path where Gradio saved the upload.
       We pass that path straight to our import tool.
    """
    if file is None:
        return "No file selected — please upload a CSV first."
    return run_tool("import_participants_csv", {"file_path": file.name})


# ─────────────────────────────────────────────
# Example prompts — shown as clickable chips
# ─────────────────────────────────────────────

EXAMPLES = [
    "Show me everyone in the panel",
    "Give me a panel overview",
    "Show me the Checkout Flow Optimisation project",
    "Who in the panel is open to interviews?",
    "Screen participants for PRJ-001",
]


# ─────────────────────────────────────────────
# UI layout
#
# 💡 gr.Blocks() is like a Figma frame — you build
#    the layout manually. gr.Row() = horizontal,
#    gr.Column() = vertical.
# ─────────────────────────────────────────────

CSS = """
    /* Centre and cap the width — feels less sprawling */
    .gradio-container { max-width: 780px !important; margin: auto !important; }

    /* Tighten up the header spacing */
    #title    { text-align: center; padding: 28px 0 4px; font-size: 1.6rem; }
    #subtitle { text-align: center; color: #888; margin: 0 0 20px; font-size: 0.95rem; }

    /* Slightly rounder chat bubbles */
    .message { border-radius: 14px !important; }

    /* Make the send button a fixed width */
    #send-btn { min-width: 72px; }

    /* Hide Gradio's footer branding */
    footer { display: none !important; }
"""

with gr.Blocks(
    theme=gr.themes.Soft(
        primary_hue="violet",   # accent colour — change to "blue", "green", etc.
        font=gr.themes.GoogleFont("Inter"),  # cleaner than the default font
    ),
    title="Research Panel Manager",
    css=CSS
) as app:

    # ── Header ───────────────────────────────────────────────────
    gr.Markdown("# 🧑‍🔬 Research Panel Manager", elem_id="title")
    gr.Markdown("AI-powered research ops assistant", elem_id="subtitle")

    # ── Per-tab session state ─────────────────────────────────────
    session_state = gr.State(create_session)

    # ── Chat window ───────────────────────────────────────────────
    chatbot = gr.Chatbot(
        value=[],
        height=460,
        show_copy_button=True,  # lets users copy Claude's responses
        bubble_full_width=False,  # tighter bubbles, easier to read
    )

    # ── Input row ─────────────────────────────────────────────────
    with gr.Row():
        msg_input = gr.Textbox(
            placeholder="Ask me about your panel, projects, or participants...",
            label="",
            scale=9,
            container=False,
            autofocus=True,
        )
        send_btn = gr.Button("Send", variant="primary", scale=1, elem_id="send-btn")

    # ── Example prompts ───────────────────────────────────────────
    gr.Examples(
        examples=EXAMPLES,
        inputs=msg_input,
        label="Try asking...",
    )

    # ── CSV Import ────────────────────────────────────────────────
    # 💡 gr.Accordion is a collapsible panel — closed by default so it
    #    doesn't take up space unless the researcher needs it.
    #    Think of it like a Details/Summary element in HTML.
    with gr.Accordion("📥 Import participants from CSV", open=False):
        gr.Markdown(
            "Upload a CSV to bulk-add participants. "
            "Use `data/sample_participants.csv` as your template — "
            "it shows all the expected columns."
        )
        with gr.Row():
            csv_upload = gr.File(
                label="CSV file",
                file_types=[".csv"],
                scale=3,
            )
            import_btn = gr.Button("Import", variant="primary", scale=1)
        import_result = gr.Textbox(
            label="Import result",
            interactive=False,
            lines=4,
            placeholder="Results will appear here after importing...",
        )

    import_btn.click(
        fn=import_csv,
        inputs=[csv_upload],
        outputs=[import_result],
    )

    # ── Clear button ──────────────────────────────────────────────
    clear_btn = gr.Button("🗑️  Clear conversation", variant="secondary", size="sm")

    # ── Wire UI events to functions ───────────────────────────────
    # 💡 .click() connects a button press to a Python function.
    #    .submit() does the same for pressing Enter in a text box.
    #
    #    inputs  = [what to pass into the function]
    #    outputs = [where to send the return values]

    send_btn.click(
        fn=respond,
        inputs=[msg_input, chatbot, session_state],
        outputs=[msg_input, chatbot, session_state],
    )
    msg_input.submit(
        fn=respond,
        inputs=[msg_input, chatbot, session_state],
        outputs=[msg_input, chatbot, session_state],
    )
    clear_btn.click(
        fn=clear_chat,
        inputs=[session_state],
        outputs=[chatbot, session_state],
    )


# ─────────────────────────────────────────────
# Launch
# ─────────────────────────────────────────────

if __name__ == "__main__":
    app.launch()
