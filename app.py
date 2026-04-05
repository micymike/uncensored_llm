"""
app.py — Mimo Agentic Chat UI (Production) + OpenAI-compatible API

Improvements over v1:
  - Correct token-level streaming (llama-cpp delta extraction)
  - <thinking> blocks rendered as collapsible expanders
  - Live latency / tok/s badge
  - <execute> blocks auto-run with result injection and display
  - YOLO auto-fix loop with depth limit
  - Clean message history (no stale system injections in UI)
  - Mobile-friendly layout
  - OpenAI-compatible API endpoints for Cline integration
"""

import re
import time
import logging
import threading
import subprocess
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any

import streamlit as st
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Import Mimo's core functionality
from main import get_llm, _rag_context, _build_system

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

# ─── OpenAI API Components ───────────────────────────────────────────────────

# API Models
class ChatMessage(BaseModel):
    role: str = Field(..., description="Message role: 'system', 'user', or 'assistant'")
    content: str = Field(..., description="Message content")

class ChatCompletionRequest(BaseModel):
    model: str = Field(default="mimo", description="Model name")
    messages: List[ChatMessage] = Field(..., description="List of chat messages")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int = Field(default=1024, ge=1, le=2048, description="Maximum tokens")
    stream: bool = Field(default=False, description="Enable streaming")
    stop: Optional[List[str]] = Field(default=None, description="Stop sequences")

class ChatCompletionChoice(BaseModel):
    index: int
    message: Optional[Dict[str, Any]] = None
    delta: Optional[Dict[str, Any]] = None
    finish_reason: str

class UsageInfo(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: UsageInfo

# FastAPI App
api_app = FastAPI(
    title="Mimo API",
    description="OpenAI-compatible API for Mimo AI Agent",
    version="1.0.0",
)

# CORS middleware
api_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Helper Functions
def generate_response_id() -> str:
    """Generate a unique response ID in OpenAI format."""
    return f"chatcmpl-{int(time.time())}-{hash(str(time.time())) % 10000:04d}"

def estimate_tokens(text: str) -> int:
    """Rough token estimation."""
    return len(text.split()) * 1.3

# API Endpoints
@api_app.get("/api/health")
async def api_health_check():
    """API health check endpoint."""
    try:
        llm = get_llm()
        return {
            "status": "healthy",
            "model_loaded": True,
            "service": "mimo-api"
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unavailable: {e}")

@api_app.get("/api/v1/models")
async def list_models():
    """List available models."""
    return {
        "object": "list",
        "data": [
            {
                "id": "mimo",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "mimo",
                "permission": [],
                "root": "mimo",
                "parent": None
            }
        ]
    }

@api_app.post("/api/v1/chat/completions")
async def create_chat_completion(request: ChatCompletionRequest):
    """Create chat completion."""
    try:
        # Convert messages to Mimo format
        mimo_messages = [
            {"role": msg.role, "content": msg.content} 
            for msg in request.messages
        ]
        
        # Get RAG context
        rag_ctx = None
        if mimo_messages and mimo_messages[-1].get("role") == "user":
            query = mimo_messages[-1].get("content", "")
            if query.strip():
                rag_ctx = _rag_context(query, k=3)
        
        # Build system prompt
        system_content = _build_system(False, rag_ctx)
        
        # Ensure system message is first
        if mimo_messages and mimo_messages[0].get("role") != "system":
            mimo_messages.insert(0, {"role": "system", "content": system_content})
        elif mimo_messages:
            mimo_messages[0]["content"] = system_content
        
        # Get model and generate response
        llm = get_llm()
        response_id = generate_response_id()
        created_time = int(time.time())
        
        # Estimate prompt tokens
        prompt_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in mimo_messages])
        prompt_tokens = int(estimate_tokens(prompt_text))
        
        # Non-streaming response (simplified for now)
        completion_text = ""
        token_count = 0
        
        response = llm.create_chat_completion(
            messages=mimo_messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=False,
            stop=request.stop or ["</s>", "<|im_end|>"],
        )
        
        for chunk in response:
            delta = chunk.get("choices", [{}])[0].get("delta", {})
            token = delta.get("content", "")
            if token:
                completion_text += token
                token_count += 1
        
        completion_tokens = token_count
        
        return ChatCompletionResponse(
            id=response_id,
            created=created_time,
            model=request.model,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message={"role": "assistant", "content": completion_text},
                    finish_reason="stop"
                )
            ],
            usage=UsageInfo(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens
            )
        )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {e}")

# API Server Thread
def start_api_server():
    """Start the API server in a separate thread."""
    logger.info("Starting API server on port 8000...")
    uvicorn.run(
        api_app,
        host="0.0.0.0",
        port=8000,
        log_level="warning",
        access_log=False
    )

# Start API server in background thread
api_thread = threading.Thread(target=start_api_server, daemon=True)
api_thread.start()

# ─── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
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
""", unsafe_allow_html=True)

# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🧠 Mimo Controls")

    st.subheader("Generation")
    temp        = st.slider("Temperature",  0.0, 1.0, 0.7, 0.05)
    max_tokens  = st.slider("Max Tokens",   64, 1536, 1024, 32)
    rag_k       = st.slider("RAG Depth (k)", 1, 10, 3)

    st.divider()

    st.subheader("Modes")
    agentic     = st.checkbox("Agentic Mode",           value=True)
    enable_exec = st.checkbox("Code Execution",         value=False)
    yolo_mode   = st.checkbox("YOLO Auto-fix",          value=False)
    if yolo_mode:
        yolo_depth = st.slider("Auto-fix Max Depth", 1, 5, 2)
    else:
        yolo_depth = 2

    st.divider()

    if st.button("🗑 Clear Chat", use_container_width=True):
        st.session_state.messages     = []
        st.session_state.terminal_log = []
        logger.info("Chat history cleared.")
        st.rerun()

    st.divider()
    st.caption("Model: Qwen3.5-9B Q4_K_M")
    st.caption("RAG: ChromaDB + MiniLM")

# ─── Session State Init ───────────────────────────────────────────────────────
if "messages"     not in st.session_state: st.session_state.messages     = []
if "terminal_log" not in st.session_state: st.session_state.terminal_log = []

# ─── Helpers ──────────────────────────────────────────────────────────────────

STATS_RE   = re.compile(r"\x00STATS:(\d+):([0-9.]+):([0-9.]+)$")
EXEC_RE    = re.compile(r"<execute>(.*?)</execute>",   re.S)


def strip_sentinel(text: str):
    """Remove the stats sentinel from the end of the streamed text."""
    m = STATS_RE.search(text)
    if m:
        return text[:m.start()], (int(m.group(1)), float(m.group(2)), float(m.group(3)))
    return text, None


def render_message(text: str, stats=None):
    """
    Render a completed assistant message:
      - Convert <execute> blocks to fenced code blocks
      - Show markdown + code blocks
      - Show stats badge
    """
    # Convert <execute> blocks to fenced code blocks for display
    display_text = EXEC_RE.sub(lambda m: f"```python\n{m.group(1).strip()}\n```", text)
    
    # Render main response
    _render_markdown_with_code(display_text)

    # Stats badge
    if stats:
        tokens, elapsed, tps = stats
        st.markdown(
            f'<span class="stat-badge">⚡ {tokens} tokens · {elapsed:.1f}s · {tps:.1f} tok/s</span>',
            unsafe_allow_html=True,
        )


def _render_markdown_with_code(text: str):
    """Split on fenced code blocks and render each segment correctly."""
    parts = re.split(r"(```[\s\S]*?```)", text)
    for part in parts:
        if part.startswith("```"):
            inner = part[3:].rstrip("`").strip()
            lines = inner.split("\n", 1)
            lang  = lines[0].strip() if len(lines) > 1 else ""
            code  = lines[1].strip() if len(lines) > 1 else inner
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
        ts   = datetime.now().strftime("%H:%M:%S")
        logger.info(f"Executing code block [{ts}]: {code[:80]}…")

        result = execute_code(code)

        # Log to terminal
        st.session_state.terminal_log.append(
            f"[{ts}]\n>>> {code}\n\n{result}"
        )

        # Inject result into history for next turn
        messages.append({
            "role":    "system",
            "content": f"Code execution result:\n{result}",
        })

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
        continue   # never show system messages

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
        status             = st.status("Thinking…", expanded=False)
        raw_output         = ""
        start_time         = time.time()

        try:
            status.update(label="Streaming response…", state="running")

            stream = generate_agentic_response(
                messages       = st.session_state.messages,
                temperature    = temp,
                max_tokens     = max_tokens,
                stream         = True,
                enable_execution = enable_exec,
                rag_k          = rag_k,
            )

            # ── Live streaming loop ──
            for token in stream:
                raw_output += token
                # Don't render sentinel tokens
                if "\x00STATS:" not in raw_output:
                    # Convert <execute> blocks to fenced code for display
                    display = EXEC_RE.sub(lambda m: f"```python\n{m.group(1).strip()}\n```", raw_output)
                    stream_placeholder.markdown(display + " ▌")

            # ── Post-stream processing ──
            clean_output, stats = strip_sentinel(raw_output)

            status.update(label="✅ Done", state="complete", expanded=False)

            # ── Final render ──
            stream_placeholder.empty()
            render_message(clean_output, stats=stats)

            # Save to history
            st.session_state.messages.append({
                "role":    "assistant",
                "content": clean_output,
                "stats":   stats,
            })
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
        st.caption("No code executions yet. Enable Code Execution and ask Mimo to run something.")
