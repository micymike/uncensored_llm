import os
import streamlit as st
import subprocess
import sys
import re
import io
import contextlib

# ---------------------------------------------------------
# 1. Configuration & Paths
# ---------------------------------------------------------
# Ensure these match your actual downloaded filename exactly
MODEL_PATH = os.getenv("LLAMA_MODEL_PATH", "Qwen3.5-9B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf")
REPO_ID = os.getenv("LLAMA_REPO_ID", "HauhauCS/Qwen3.5-9B-Uncensored-HauhauCS-Aggressive")

# ---------------------------------------------------------
# 2. Lazy Loader (Prevents the "Accessing Path" hang)
# ---------------------------------------------------------
@st.cache_resource
def get_llm():
    """Loads the model only when needed to prevent boot-up hangs."""
    from llama_cpp import Llama
    
    if os.path.exists(MODEL_PATH):
        st.info(f"Loading local model: {MODEL_PATH}")
        return Llama(model_path=MODEL_PATH, n_ctx=4096, n_threads=4) # Adjust threads based on CPU
    
    st.warning("Local model not found. Attempting to stream from Hugging Face...")
    return Llama.from_pretrained(repo_id=REPO_ID, filename=MODEL_PATH, n_ctx=4096)

# ---------------------------------------------------------
# 3. Tool: Code Execution (Sandbox)
# ---------------------------------------------------------
def execute_code(code):
    """Execute Python code in a subprocess and return output."""
    try:
        # Use the current python executable to run the string
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=15  
        )
        output = result.stdout
        error = result.stderr
        return f"Output:\n{output}\nError:\n{error}" if error else f"Output:\n{output}"
    except subprocess.TimeoutExpired:
        return "Execution timed out (15s limit)."
    except Exception as e:
        return f"Execution failed: {str(e)}"

# ---------------------------------------------------------
# 4. Agentic Logic
# ---------------------------------------------------------
def generate_agentic_response(messages, temperature=0.7, max_tokens=1024, stream=True, chain_of_thought=False, enable_execution=False):
    """Orchestrates the LLM response with optional RAG and Tools."""
    
    # Lazy load RAG inside the function
    from rag import retrieve
    llm = get_llm()

    # System Prompts
    agent_system_prompt = {
        "role": "system",
        "content": "You are Mimo, an expert AI Agent. Reason before acting. Use clean code."
    }
    
    full_messages = [agent_system_prompt]

    if chain_of_thought:
        full_messages.append({
            "role": "system", 
            "content": "Provide a 'Final Answer:' section after your reasoning."
        })

    if enable_execution:
        full_messages.append({
            "role": "system",
            "content": "To run code, use <execute>your_code_here</execute> tags."
        })

    # RAG Injection
    try:
        if messages and messages[-1].get("role") == "user":
            query = messages[-1].get("content", "")
            snippets = retrieve(query, k=3)
            if snippets:
                context_text = "\n\n".join([f"Source: {item['path']}\n{item['text']}" for item in snippets])
                full_messages.append({
                    "role": "system",
                    "content": f"Context for your answer:\n{context_text}"
                })
    except Exception as e:
        print(f"RAG Error: {e}")

    full_messages += messages

    completion_stream = llm.create_chat_completion(
        messages=full_messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=stream,
    )

    if stream:
        for chunk in completion_stream:
            yield chunk["choices"][0].get("delta", {}).get("content", "")
    else:
        yield completion_stream["choices"][0]["message"]["content"]

# Backward compatibility
def generate_response(prompt, temperature=0.8, max_tokens=512):
    return generate_agentic_response([{"role": "user", "content": prompt}], temperature, max_tokens)
