import os
import streamlit as st
from llama_cpp import Llama
from rag import retrieve
import subprocess
import sys
import re

# CORRECTED PATHS
MODEL_PATH = os.getenv("LLAMA_MODEL_PATH", "Qwen3.5-9B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf")
REPO_ID = os.getenv("LLAMA_REPO_ID", "HauhauCS/Qwen3.5-9B-Uncensored-HauhauCS-Aggressive")

@st.cache_resource
def get_llm():
    """Loads the model once and keeps it in memory."""
    # Check if file exists in the current directory
    if os.path.exists(MODEL_PATH):
        print(f"--- Loading local model from {MODEL_PATH} ---")
        return Llama(model_path=MODEL_PATH, n_ctx=4096)
    
    print(f"--- Local model not found, attempting download for {MODEL_PATH} ---")
    return Llama.from_pretrained(repo_id=REPO_ID, filename=MODEL_PATH, n_ctx=4096)

def execute_code(code):
    """Execute Python code in a safe subprocess."""
    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=10
        )
        return f"Output:\n{result.stdout}\nError:\n{result.stderr}" if result.stderr else f"Output:\n{result.stdout}"
    except Exception as e:
        return f"Execution failed: {e}"
