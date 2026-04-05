import os
import streamlit as st
import subprocess
import sys
import logging

# Set up silent logging for production
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MimoEngine")

# --- Configuration ---
MODEL_PATH = os.getenv("LLAMA_MODEL_PATH", "Qwen3.5-9B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf")
REPO_ID = os.getenv("LLAMA_REPO_ID", "HauhauCS/Qwen3.5-9B-Uncensored-HauhauCS-Aggressive")

@st.cache_resource
def get_llm():
    """Loads the model with production-grade memory optimization."""
    from llama_cpp import Llama
    
    # Check for local file first
    if os.path.exists(MODEL_PATH):
        return Llama(
            model_path=MODEL_PATH,
            n_ctx=4096,
            n_threads=4,      # Optimized for VPS vCPUs
            use_mmap=True,    # Fast disk-to-RAM mapping
            use_mlock=True,   # Prevents OS from moving model to swap (keeps it fast)
            verbose=False     # Silences massive terminal logs
        )
    
    # Fallback to HF if local is missing
    return Llama.from_pretrained(
        repo_id=REPO_ID, 
        filename=MODEL_PATH, 
        n_ctx=4096,
        n_threads=4,
        verbose=False
    )

def execute_code(code):
    """Securely execute Python code and return captured output."""
    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=15
        )
        return f"Output:\n{result.stdout}\nError:\n{result.stderr}" if result.stderr else f"Output:\n{result.stdout}"
    except subprocess.TimeoutExpired:
        return "Execution timed out (15s limit)."
    except Exception as e:
        return f"Execution failed: {str(e)}"

def generate_agentic_response(messages, temperature=0.7, max_tokens=1024, chain_of_thought=True, enable_execution=False):
    """The core logic for Mimo's thinking and action cycle."""
    from rag import retrieve # Lazy load RAG
    llm = get_llm()

    # Persona & Thinking Instructions
    system_content = (
        "You are Mimo, an expert AI Agent. "
        "Before answering, you MUST show your reasoning inside <thinking> tags. "
        "Example: <thinking>Step 1... Step 2...</thinking> Final Answer: [Answer]"
    )
    
    full_messages = [{"role": "system", "content": system_content}]
    
    if enable_execution:
        full_messages.append({
            "role": "system", 
            "content": "To execute code, use <execute>python_code</execute> tags."
        })

    # Silent RAG Injection
    try:
        if messages and messages[-1].get("role") == "user":
            query = messages[-1].get("content", "")
            snippets = retrieve(query, k=3)
            if snippets:
                context = "\n".join([f"Context: {s['text']}" for s in snippets])
                full_messages.append({"role": "system", "content": f"Relevant context:\n{context}"})
    except Exception:
        pass # Silent fail for RAG to keep UI clean

    full_messages += messages

    return llm.create_chat_completion(
        messages=full_messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
    )
