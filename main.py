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
MODEL_PATH = os.getenv(
    "LLAMA_MODEL_PATH", "Qwen3.5-9B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf"
)
REPO_ID = os.getenv(
    "LLAMA_REPO_ID", "HauhauCS/Qwen3.5-9B-Uncensored-HauhauCS-Aggressive"
)
N_CTX = int(os.getenv("LLAMA_N_CTX", "16384"))  # 16384 for larger context
N_THREADS = int(os.getenv("LLAMA_N_THREADS", "4"))
N_GPU_LAYERS = int(os.getenv("LLAMA_N_GPU", "0"))  # set >0 if CUDA available
EXEC_TIMEOUT = int(os.getenv("EXEC_TIMEOUT", "15"))

# ─── Model Singleton (thread-safe lazy load) ──────────────────────────────────
_llm_lock = threading.Lock()
_llm_cache = {"model": None}


def get_llm():
    """Thread-safe singleton loader. First call pays the load cost; subsequent calls are free."""
    if _llm_cache["model"] is not None:
        return _llm_cache["model"]

    with _llm_lock:
        if _llm_cache["model"] is not None:  # double-checked locking
            return _llm_cache["model"]

        logger.info("Loading model…")
        t0 = time.time()

        from llama_cpp import Llama

        kwargs = dict(
            n_ctx=N_CTX,
            n_threads=N_THREADS,
            n_gpu_layers=N_GPU_LAYERS,
            use_mmap=True,  # mmap lets OS page in/out safely
            use_mlock=False,  # NEVER lock on 8GB VPS — causes OOM kill
            verbose=False,
        )

        if os.path.exists(MODEL_PATH):
            logger.info(f"Loading from local path: {MODEL_PATH}")
            model = Llama(model_path=MODEL_PATH, **kwargs)
        else:
            logger.info(f"Downloading from HF: {REPO_ID}")
            model = Llama.from_pretrained(
                repo_id=REPO_ID, filename=MODEL_PATH, **kwargs
            )

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


# ─── Tool Definitions ──────────────────────────────────────────────────────────
AVAILABLE_TOOLS = {
    "execute_code": {
        "name": "execute_code",
        "description": "Execute Python code in a sandboxed environment. Use for running calculations, code debugging, or any computational task.",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "The Python code to execute"}
            },
            "required": ["code"],
        },
    },
    "web_search": {
        "name": "web_search",
        "description": "Search the web for current information. Use for finding up-to-date facts, news, or documentation.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Search query"}},
            "required": ["query"],
        },
    },
    "browser_navigate": {
        "name": "browser_navigate",
        "description": "Navigate to a URL and get the page content. Use for browsing websites, reading articles, or interacting with web pages.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to navigate to"},
                "action": {
                    "type": "string",
                    "description": "Action to perform: 'goto', 'screenshot', 'get_content', 'click', 'fill'",
                },
            },
            "required": ["url", "action"],
        },
    },
}


def execute_tool(tool_name: str, arguments: dict) -> str:
    """Execute a tool and return the result."""
    if tool_name == "execute_code":
        return execute_code(arguments.get("code", ""))
    elif tool_name == "web_search":
        from main import web_search

        return web_search(arguments.get("query", ""))
    elif tool_name == "browser_navigate":
        from main import browser_action

        return browser_action(
            arguments.get("url", ""), arguments.get("action", "get_content")
        )
    else:
        return f"Unknown tool: {tool_name}"


# ─── System Prompt Builder ────────────────────────────────────────────────────
_BASE_SYSTEM = """You are Mimo, an expert AI Agent built for precision and speed.

CRITICAL: NEVER show your thinking process in the final response. Use <thinking> tags for internal reasoning.

RESPONSE RULES:
- When you need to reason through a problem, use <thinking>...</thinking> tags - this will be hidden from users
- when the question doesn't require a code, DO NOT produce a code.
- When the user ask a question that depends on text generation and not code execution, DO NOT produce a code, answer directly through text generation
- Use markdown for structure; use fenced code blocks with language tags
- When you execute code, wrap it: <execute>python_code_here</execute>
- Cite retrieved context when used; don't hallucinate sources
- Be concise and to the point

Example for "hello": "Hello! I am Mimo, your expert AI Agent. How can I help you today?"
"""


def _build_system(
    enable_execution: bool, rag_context: Optional[str], agentic_mode: bool = False
) -> str:
    system = _BASE_SYSTEM.strip()

    # Tool definitions
    tools_json = """\n\nAVAILABLE TOOLS:
- execute_code: Execute Python code in sandboxed environment. Parameters: code (string)
- web_search: Search the web for current information. Parameters: query (string)  
- browser_navigate: Browse websites using Playwright. Parameters: url (string), action (string: 'goto', 'screenshot', 'get_content', 'click', 'fill')

When you need to use a tool, respond with:
<tool>
<tool_name>execute_code</tool_name>
<arguments>{"code": "your python code here"}</arguments>
</tool>"""

    if enable_execution or agentic_mode:
        system += tools_json

    if agentic_mode:
        system += """

AGENTIC MODE:
- You can use tools to help complete complex tasks
- After using a tool, analyze the result and continue your response
- If your response is cut off, another iteration will continue from where you left off
- Keep your response complete and thorough"""

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
import re

TOOL_CALL_RE = re.compile(
    r"<tool>\s*<tool_name>(\w+)</tool_name>\s*<arguments>(.+?)</arguments>\s*</tool>",
    re.S,
)
WEB_SEARCH_AVAILABLE = True


def web_search(query: str) -> str:
    """Web search using Exa API."""
    try:
        from exa_py import Exa

        exa = Exa()
        results = exa.search(query, num_results=5)
        return "\n".join(f"- {r.title}: {r.url}" for r in results.results)
    except ImportError:
        return "web_search tool not available. Install exa-py: pip install exa-py"
    except Exception as e:
        return f"Search failed: {e}"


_browser_context = None


def browser_action(url: str, action: str = "get_content") -> str:
    """Browse websites - tries lightweight HTTP first, falls back to Playwright."""

    # Lightweight HTTP approach (default)
    try:
        import requests
        from bs4 import BeautifulSoup

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        if action in ("goto", "get_content"):
            resp = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(resp.text, "html.parser")

            # Remove script/style elements
            for tag in soup(["script", "style"]):
                tag.decompose()

            text = soup.get_text(separator="\n", strip=True)
            # Clean up whitespace
            lines = [line for line in text.split("\n") if line.strip()]
            cleaned = "\n".join(lines[:200])  # Limit lines

            return f"Loaded {url}\n\n{cleaned[:15000]}"

        elif action == "screenshot":
            # Can't do screenshots with requests - fall back to description
            return "Screenshot not available with lightweight mode. Use Playwright for screenshots."

    except ImportError:
        pass  # Fall through to Playwright
    except Exception as e:
        pass  # Fall through to Playwright

    # Fallback to Playwright (heavy but full features)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return "browser_navigate tool not available. Install playwright: pip install playwright && playwright install chromium"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            if action == "goto" or action == "get_content":
                page.goto(url, timeout=30000)
                content = page.content()
                browser.close()
                return f"Loaded {url}\n\n{content[:10000]}"
            elif action == "screenshot":
                page.goto(url, timeout=30000)
                import base64

                screenshot = page.screenshot()
                browser.close()
                return f"Screenshot (base64): {base64.b64encode(screenshot).decode()[:100]}..."
            elif action == "get_content":
                page.goto(url, timeout=30000)
                text = page.inner_text("body") or ""
                browser.close()
                return f"Page content from {url}:\n\n{text[:10000]}"
            else:
                browser.close()
                return f"Unknown action: {action}. Use: goto, screenshot, get_content"

    except Exception as e:
        return f"Browser error: {e}"


def generate_agentic_response(
    messages: List[Dict],
    temperature: float = 0.7,
    max_tokens: int = 4096,
    stream: bool = True,
    enable_execution: bool = False,
    rag_k: int = 3,
    agentic_mode: bool = False,
    max_iterations: int = 5,
) -> Generator[str, None, None]:
    """
    Yields text tokens one-by-one.
    Handles RAG injection, system prompt assembly, tool execution, and agentic continuation.
    """
    llm = get_llm()

    # Build system prompt
    rag_ctx = None
    if messages and messages[-1].get("role") == "user":
        query = messages[-1].get("content", "")
        if query.strip():
            rag_ctx = _rag_context(query, k=rag_k)

    system_msg = {
        "role": "system",
        "content": _build_system(enable_execution, rag_ctx, agentic_mode),
    }
    full_messages = [system_msg] + [m for m in messages if m.get("role") != "system"]

    iteration = 0
    final_output = ""
    pending_tool_calls = []

    while iteration < max_iterations:
        iteration += 1
        logger.info(f"Agentic iteration {iteration}/{max_iterations}")

        # Prepare messages with any pending tool results
        msg_list = full_messages + pending_tool_calls
        pending_tool_calls = []

        logger.info(
            f"Generating | temp={temperature} max_tokens={max_tokens} rag={'yes' if rag_ctx else 'no'} agentic={agentic_mode}"
        )
        t0 = time.time()
        token_count = 0

        try:
            response = llm.create_chat_completion(
                messages=msg_list,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream,
                stop=["</s>", "<|im_end|>"],
            )

            current_response = ""

            for chunk in response:
                delta = chunk.get("choices", [{}])[0].get("delta", {})
                token = delta.get("content", "")
                if token:
                    token_count += 1
                    current_response += token
                    yield token

            final_output += current_response

            # Check for tool calls
            tool_matches = list(TOOL_CALL_RE.finditer(current_response))

            if not tool_matches:
                # No tools, response complete
                break

            # Execute tools and add results
            for match in tool_matches:
                tool_name = match.group(1)
                args_str = match.group(2)

                try:
                    import json

                    arguments = json.loads(args_str)
                except:
                    arguments = {"raw": args_str}

                logger.info(f"Executing tool: {tool_name}")
                result = execute_tool(tool_name, arguments)

                # Add tool result to messages
                pending_tool_calls.append(
                    {
                        "role": "tool",
                        "content": f"<result>{tool_name}: {result}</result>",
                    }
                )

                # Also add to output so user sees tool use
                yield f"\n\n*Tool: {tool_name}*\n```\n{result}\n```\n\n"

            # If not agentic mode, don't continue
            if not agentic_mode:
                break

        except Exception as exc:
            logger.error(f"Streaming error: {exc}")
            yield f"\n\n⚠️ Generation error: {exc}"
            break
        finally:
            elapsed = time.time() - t0
            tps = token_count / elapsed if elapsed > 0 else 0
            logger.info(
                f"Iteration {iteration} | {token_count} tokens | {elapsed:.2f}s | {tps:.1f} tok/s"
            )

    # Yield stats
    yield f"\x00STATS:{iteration}:{token_count}:{elapsed:.2f}:{tps:.1f}"
