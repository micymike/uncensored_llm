"""
app.py — Mimo Agentic Chat UI (Production)

Improvements over v1:
  - Correct token-level streaming (llama-cpp delta extraction)
  - <thinking> blocks rendered as collapsible expanders
  - Live latency / tok/s badge
  - <execute> blocks auto-run with result injection and display
  - YOLO auto-fix loop with depth limit
  - Clean message history (no stale system injections in UI)
  - Mobile-friendly layout
"""

import re
import time
import logging
from datetime import datetime

import streamlit as st

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("MimoUI")

# ─── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Mimo · Agentic AI",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
/* Monospace terminal feel for code */
code { font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 0.85rem; }

/* Stats badge */
.stat-badge {
    display: inline-block;
    background: #0f172a;
    color: #38bdf8;
    font-size: 0.72rem;
    font-family: monospace;
    padding: 2px 10px;
    border-radius: 999px;
    border: 1px solid #1e40af;
    margin-top: 6px;
}

/* Execution result block */
.exec-result {
    background: #0d1117;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 10px 14px;
    font-family: monospace;
    font-size: 0.8rem;
    color: #7ee787;
    margin-top: 6px;
}
</style>
""",
    unsafe_allow_html=True,
)

# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🧠 Mimo Controls")

    st.subheader("Generation")
    temp = st.slider("Temperature", 0.0, 1.0, 0.7, 0.05)
    max_tokens = st.slider("Max Tokens", 64, 8192, 4096, 64)
    rag_k = st.slider("RAG Depth (k)", 1, 10, 3)

    st.divider()

    st.subheader("Modes")
    agentic = st.checkbox("Agentic Mode", value=True)
    if agentic:
        max_iterations = st.slider("Max Iterations", 1, 10, 5)
    else:
        max_iterations = 1
    enable_exec = st.checkbox("Code Execution", value=False)
    yolo_mode = st.checkbox("YOLO Auto-fix", value=False)
    if yolo_mode:
        yolo_depth = st.slider("Auto-fix Max Depth", 1, 5, 2)
    else:
        yolo_depth = 2

    st.divider()

    if st.button("🗑 Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.terminal_log = []
        logger.info("Chat history cleared.")
        st.rerun()

    st.divider()
    st.caption("Model: Qwen3.5-9B Q4_K_M")
    st.caption("RAG: ChromaDB + MiniLM")

# ─── Session State Init ───────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "terminal_log" not in st.session_state:
    st.session_state.terminal_log = []

# ─── Helpers ──────────────────────────────────────────────────────────────────

STATS_RE = re.compile(r"\x00STATS:(\d+):([0-9.]+):([0-9.]+):([0-9.]+)$")
EXEC_RE = re.compile(r"<execute>(.*?)</execute>", re.S)
THINK_RE = re.compile(r"<thinking>(.*?)</thinking>", re.S)
TOOL_RE = re.compile(
    r"<tool>\s*<tool_name>(\w+)</tool_name>\s*<arguments>(.+?)</arguments>\s*</tool>",
    re.S,
)


def strip_sentinel(text: str):
    """Remove the stats sentinel from the end of the streamed text."""
    m = STATS_RE.search(text)
    if m:
        # New format: iterations:token_count:elapsed:tps
        return text[: m.start()], (
            int(m.group(1)),  # iterations
            int(m.group(2)),  # token_count
            float(m.group(3)),  # elapsed
            float(m.group(4)),  # tps
        )
    return text, None


def extract_thinking(text: str) -> tuple:
    """Extract thinking blocks and return (clean_text, thinking_content)."""
    thinking_blocks = THINK_RE.findall(text)
    clean_text = THINK_RE.sub("", text)
    return clean_text, thinking_blocks


def render_message(text: str, stats=None):
    """
    Render a completed assistant message:
      - Convert <execute> blocks to fenced code blocks
      - Show <thinking> blocks in collapsible expander
      - Show markdown + code blocks
      - Show stats badge
    """
    # Extract and remove thinking blocks
    display_text, thinking_blocks = extract_thinking(text)

    # Convert <execute> blocks to fenced code blocks for display
    display_text = EXEC_RE.sub(
        lambda m: f"```python\n{m.group(1).strip()}\n```", display_text
    )

    # Render thinking in collapsible expander (Claude style)
    if thinking_blocks:
        with st.expander("🤔 Thinking", expanded=False):
            for block in thinking_blocks:
                st.markdown(block)

    # Render main response
    _render_markdown_with_code(display_text)

    # Stats badge
    if stats:
        iterations, tokens, elapsed, tps = stats
        iter_info = f" · {iterations} iter" if iterations > 1 else ""
        st.markdown(
            f'<span class="stat-badge">⚡ {tokens} tokens · {elapsed:.1f}s · {tps:.1f} tok/s{iter_info}</span>',
            unsafe_allow_html=True,
        )


def _render_markdown_with_code(text: str):
    """Split on fenced code blocks and render each segment correctly."""
    parts = re.split(r"(```[\s\S]*?```)", text)
    for part in parts:
        if part.startswith("```"):
            inner = part[3:].rstrip("`").strip()
            lines = inner.split("\n", 1)
            lang = lines[0].strip() if len(lines) > 1 else ""
            code = lines[1].strip() if len(lines) > 1 else inner
            st.code(code, language=lang or "python")
        elif part.strip():
            st.markdown(part)


def run_code_blocks(text: str, messages: list, temp: float, max_tokens: int) -> str:
    """
    Find all <execute> blocks, run them, inject results into message history,
    and return the augmented text with results appended.
    """
    from main import execute_code, generate_agentic_response

    exec_blocks = EXEC_RE.findall(text)
    if not exec_blocks:
        return text

    augmented = text
    for code in exec_blocks:
        code = code.strip()
        ts = datetime.now().strftime("%H:%M:%S")
        logger.info(f"Executing code block [{ts}]: {code[:80]}…")

        result = execute_code(code)

        # Log to terminal
        st.session_state.terminal_log.append(f"[{ts}]\n>>> {code}\n\n{result}")

        # Inject result into history for next turn
        messages.append(
            {
                "role": "system",
                "content": f"Code execution result:\n{result}",
            }
        )

        # Append rendered result to visible text
        augmented += f"\n\n**Execution result:**\n```text\n{result}\n```"

        # YOLO auto-fix if errors detected
        if yolo_mode and ("Error" in result or "Traceback" in result):
            fix_text = ""
            for fix_token in generate_agentic_response(
                messages, temperature=temp, max_tokens=max_tokens
            ):
                if not fix_token.startswith("\x00STATS:"):
                    fix_text += fix_token
            augmented += f"\n\n**Auto-fix attempt:**\n{fix_text}"
            messages.append({"role": "assistant", "content": fix_text})

    return augmented


# ─── Header ───────────────────────────────────────────────────────────────────
st.title("🧠 Mimo · Agentic Chat")
col_left, col_right = st.columns([3, 1])
with col_right:
    st.caption(f"CPU · {max_tokens} max tokens")

st.divider()

# ─── Chat History ─────────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    if msg["role"] == "system":
        continue  # never show system messages

    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant":
            render_message(
                msg.get("content", ""),
                stats=msg.get("stats"),
            )
        else:
            st.markdown(msg.get("content", ""))

# ─── Input ────────────────────────────────────────────────────────────────────
user_prompt = st.chat_input("Ask Mimo anything…")

if user_prompt:
    from main import generate_agentic_response

    logger.info(f"User: {user_prompt[:80]}")
    st.session_state.messages.append({"role": "user", "content": user_prompt})

    with st.chat_message("user"):
        st.markdown(user_prompt)

    with st.chat_message("assistant"):
        stream_placeholder = st.empty()
        status = st.status("Thinking…", expanded=False)
        raw_output = ""
        start_time = time.time()

        try:
            status.update(label="Streaming response…", state="running")

            stream = generate_agentic_response(
                messages=st.session_state.messages,
                temperature=temp,
                max_tokens=max_tokens,
                stream=True,
                enable_execution=enable_exec,
                rag_k=rag_k,
                agentic_mode=agentic,
                max_iterations=max_iterations,
            )

            # ── Live streaming loop ──
            thinking_placeholder = None
            current_thinking = ""

            for token in stream:
                raw_output += token

                # Extract thinking blocks for live display
                _, thinking_blocks = extract_thinking(raw_output)
                if thinking_blocks and thinking_placeholder is None:
                    thinking_placeholder = st.empty()
                    current_thinking = thinking_blocks[-1]
                    with thinking_placeholder.container():
                        with st.expander("🤔 Thinking", expanded=True):
                            st.markdown(current_thinking)

                # Don't render sentinel tokens
                if "\x00STATS:" not in raw_output:
                    # Extract and hide thinking for live display
                    clean_for_display, _ = extract_thinking(raw_output)
                    # Convert <execute> blocks to fenced code for display
                    display = EXEC_RE.sub(
                        lambda m: f"```python\n{m.group(1).strip()}\n```",
                        clean_for_display,
                    )
                    stream_placeholder.markdown(display + " ▌")

            # ── Post-stream processing ──
            clean_output, stats = strip_sentinel(raw_output)

            status.update(label="✅ Done", state="complete", expanded=False)

            # ── Final render ──
            stream_placeholder.empty()
            render_message(clean_output, stats=stats)

            # Save to history
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": clean_output,
                    "stats": stats,
                }
            )
            logger.info(f"Response complete. Stats: {stats}")

        except Exception as err:
            status.update(label="❌ Error", state="error")
            logger.exception(f"Generation error: {err}")
            st.error(f"**Generation failed:** {err}")

# ─── Terminal Panel ───────────────────────────────────────────────────────────
st.divider()

with st.expander("🖥️ Execution Terminal", expanded=bool(st.session_state.terminal_log)):
    if st.session_state.terminal_log:
        terminal_text = "\n\n" + ("─" * 60 + "\n\n").join(st.session_state.terminal_log)
        st.code(terminal_text, language="text")
        if st.button("Clear Terminal"):
            st.session_state.terminal_log = []
            st.rerun()
    else:
        st.caption(
            "No code executions yet. Enable Code Execution and ask Mimo to run something."
        )
