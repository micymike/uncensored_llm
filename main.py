import os
import sys
import subprocess
import logging
import time
import hashlib
import threading
from functools import lru_cache
from typing import Generator, List, Dict, Optional

# ─── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("MimoEngine")

# ─── Configuration ────────────────────────────────────────────────────────────
MODEL_PATH   = os.getenv("LLAMA_MODEL_PATH", "Qwen3.5-9B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf")
REPO_ID      = os.getenv("LLAMA_REPO_ID",   "HauhauCS/Qwen3.5-9B-Uncensored-HauhauCS-Aggressive")
N_CTX        = int(os.getenv("LLAMA_N_CTX",      "2048"))  # 2048 saves ~500MB vs 4096
N_THREADS    = int(os.getenv("LLAMA_N_THREADS",  "4"))
N_GPU_LAYERS = int(os.getenv("LLAMA_N_GPU",      "0"))   # set >0 if CUDA available
EXEC_TIMEOUT = int(os.getenv("EXEC_TIMEOUT",     "15"))

# ─── Model Singleton (thread-safe lazy load) ──────────────────────────────────
_llm_lock   = threading.Lock()
_llm_cache  = {"model": None}

def get_llm():
    """Thread-safe singleton loader. First call pays the load cost; subsequent calls are free."""
    if _llm_cache["model"] is not None:
        return _llm_cache["model"]

    with _llm_lock:
        if _llm_cache["model"] is not None:   # double-checked locking
            return _llm_cache["model"]

        logger.info("Loading model…")
        t0 = time.time()

        from llama_cpp import Llama

        kwargs = dict(
            n_ctx=N_CTX,
            n_threads=N_THREADS,
            n_gpu_layers=N_GPU_LAYERS,
            use_mmap=True,       # mmap lets OS page in/out safely
            use_mlock=False,     # NEVER lock on 8GB VPS — causes OOM kill
            verbose=False,
        )

        if os.path.exists(MODEL_PATH):
            logger.info(f"Loading from local path: {MODEL_PATH}")
            model = Llama(model_path=MODEL_PATH, **kwargs)
        else:
            logger.info(f"Downloading from HF: {REPO_ID}")
            model = Llama.from_pretrained(repo_id=REPO_ID, filename=MODEL_PATH, **kwargs)

        _llm_cache["model"] = model
        logger.info(f"Model ready in {time.time() - t0:.1f}s")
        return model


# ─── Safe Code Execution ──────────────────────────────────────────────────────
def execute_code(code: str) -> str:
    """
    Run arbitrary Python in a subprocess with a hard timeout.
    Returns a structured result string.
    """
    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=EXEC_TIMEOUT,
        )
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        parts = []
        if stdout:
            parts.append(f"stdout:\n{stdout}")
        if stderr:
            parts.append(f"stderr:\n{stderr}")
        if not parts:
            parts.append("(no output)")
        return "\n\n".join(parts)

    except subprocess.TimeoutExpired:
        return f"⏱ Execution timed out after {EXEC_TIMEOUT}s."
    except Exception as exc:
        return f"❌ Execution failed: {exc}"


# ─── System Prompt Builder ────────────────────────────────────────────────────
_BASE_SYSTEM = """You are Mimo, an expert AI Agent built for precision and speed.

CRITICAL: NEVER show your thinking process, analysis, or internal monologue. Respond directly and immediately.

RESPONSE RULES:
- Give the answer directly without any explanation of your thought process
- Use markdown for structure; use fenced code blocks with language tags
- When you execute code, wrap it: <execute>python_code_here</execute>
- Cite retrieved context when used; don't hallucinate sources
- Be concise and to the point

Example for "hello": "Hello! I am Mimo, your expert AI Agent. How can I help you today?"
"""

def _build_system(enable_execution: bool, rag_context: Optional[str]) -> str:
    system = _BASE_SYSTEM.strip()
    if enable_execution:
        system += "\n\nCODE EXECUTION: Wrap runnable Python in <execute>…</execute>. You WILL see the output."
    if rag_context:
        system += f"\n\nRETRIEVED CONTEXT (use if relevant, cite by saying 'From docs:'):\n{rag_context}"
    return system


# ─── RAG Helper ───────────────────────────────────────────────────────────────
@lru_cache(maxsize=128)
def _cached_retrieve(query_hash: str, query: str, k: int) -> tuple:
    """LRU-cached retrieval so identical queries don't hit ChromaDB twice."""
    try:
        from rag import retrieve
        snippets = retrieve(query, k=k)
        return tuple(s["text"] for s in snippets)
    except Exception as exc:
        logger.warning(f"RAG retrieval failed: {exc}")
        return ()


def _rag_context(query: str, k: int = 3) -> Optional[str]:
    key = hashlib.md5(query.encode()).hexdigest()
    snippets = _cached_retrieve(key, query, k)
    if not snippets:
        return None
    return "\n---\n".join(snippets)


# ─── Core Generator ───────────────────────────────────────────────────────────
def generate_agentic_response(
    messages: List[Dict],
    temperature: float = 0.7,
    max_tokens: int = 1024,
    stream: bool = True,
    enable_execution: bool = False,
    rag_k: int = 3,
) -> Generator[str, None, None]:
    """
    Yields text tokens one-by-one.
    Handles RAG injection, system prompt assembly, and safe streaming.
    """
    llm = get_llm()

    # ── RAG ──
    rag_ctx = None
    if messages and messages[-1].get("role") == "user":
        query = messages[-1].get("content", "")
        if query.strip():
            rag_ctx = _rag_context(query, k=rag_k)

    # ── Assemble message list ──
    system_msg = {"role": "system", "content": _build_system(enable_execution, rag_ctx)}
    full_messages = [system_msg] + [
        m for m in messages if m.get("role") != "system"   # strip old system injections
    ]

    logger.info(f"Generating | temp={temperature} max_tokens={max_tokens} rag={'yes' if rag_ctx else 'no'}")
    t0 = time.time()
    token_count = 0

    # ── Stream ──
    try:
        response = llm.create_chat_completion(
            messages=full_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            stop=["</s>", "<|im_end|>"],
        )

        for chunk in response:
            delta = chunk.get("choices", [{}])[0].get("delta", {})
            token = delta.get("content", "")
            if token:
                token_count += 1
                yield token

    except Exception as exc:
        logger.error(f"Streaming error: {exc}")
        yield f"\n\n⚠️ Generation error: {exc}"
    finally:
        elapsed = time.time() - t0
        tps = token_count / elapsed if elapsed > 0 else 0
        logger.info(f"Done | {token_count} tokens | {elapsed:.2f}s | {tps:.1f} tok/s")
        # Yield metadata as a special sentinel for the UI to pick up
        yield f"\x00STATS:{token_count}:{elapsed:.2f}:{tps:.1f}"
