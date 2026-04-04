import os
import streamlit as st
from llama_cpp import Llama

from rag import retrieve

import subprocess
import sys
import io
import contextlib

MODEL_PATH = os.getenv("LLAMA_MODEL_PATH", "Qwen3.5-9B-Uncensored-HauhauCS-Aggressive-Q8_0.gguf")
REPO_ID = os.getenv("LLAMA_REPO_ID", "HauhauCS/Qwen3.5-9B-Uncensored-HauhauCS-Aggressive")

# ---------------
# Model loader
# ---------------
@st.cache_resource
def get_llm():
    """Loads the model once and keeps it in memory."""
    if os.path.exists(MODEL_PATH):
        return Llama(model_path=MODEL_PATH, n_ctx=4096)

    return Llama.from_pretrained(repo_id=REPO_ID, filename=MODEL_PATH, n_ctx=4096)

# ---------------
# Code execution tool (sandbox)
# ---------------
def execute_code(code):
    """Execute Python code in a safe subprocess and return output."""
    try:
        # Use subprocess to run code in isolation
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=10  # 10 second timeout
        )
        output = result.stdout
        error = result.stderr
        return f"Output:\n{output}\nError:\n{error}" if error else f"Output:\n{output}"
    except subprocess.TimeoutExpired:
        return "Execution timed out."
    except Exception as e:
        return f"Execution failed: {e}"


# ---------------
# Agentic response builder (ReAct style)
# ---------------
def generate_agentic_response(messages, temperature=0.7, max_tokens=1024, stream=True, chain_of_thought=False, enable_execution=False):
    """Yields the model text in chunks for streaming in the UI."""
    llm = get_llm()

    agent_system_prompt = {
        "role": "system",
        "content": (
            "You are an expert AI Agent. For complex coding tasks: "
            "1. Analyze the requirements. 2. Plan the solution step-by-step. "
            "3. Write clean, efficient code. 4. Self-critique for potential bugs. "
            "For operational commands, reason and act in ReAct style if needed. "
        ),
    }
    
    cot_prompt = None
    if chain_of_thought:
        cot_prompt = {
            "role": "system",
            "content": (
                "To show deeper reasoning, explicitly outline your chain of thought before "
                "you provide the final code. Format as:\n" 
                "[Thought 1], [Thought 2], ... , then final response.\n"
                "Include a clear \"Final Answer:\" section at the end."
            ),
        }

    exec_prompt = None
    if enable_execution:
        exec_prompt = {
            "role": "system",
            "content": (
                "You can execute Python code to test your solutions. "
                "To run code, wrap it in <execute> tags like: <execute>print('hello')</execute>. "
                "The system will run it and provide the output in the next message."
            ),
        }

    # add RAG context when available
    rag_context = []
    try:
        if messages and messages[-1].get("role") == "user":
            query = messages[-1].get("content", "")
            snippets = retrieve(query, k=4)
            if snippets:
                context_text = "\n\n".join([f"Source: {item['path']}\n{item['text']}" for item in snippets])
                rag_context.append({
                    "role": "system",
                    "content": (
                        "When answering this user query about Python, reference the following documentation snippets. "
                        "If the answer is in the docs, quote them and cite paths. "
                        "Do not hallucinate facts outside the referenced docs unless absolutely needed.\n\n"
                        + context_text
                    ),
                })
    except Exception:
        # If RAG fails, continue without docs
        rag_context = []

    full_messages = [agent_system_prompt]
    if cot_prompt is not None:
        full_messages.append(cot_prompt)
    if exec_prompt is not None:
        full_messages.append(exec_prompt)
    full_messages += rag_context + messages

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
        text = completion_stream["choices"][0]["message"]["content"]
        yield text


# Backward compatibility helper
def generate_response(prompt, temperature=0.8, max_tokens=512):
    return generate_agentic_response([{"role": "user", "content": prompt}], temperature, max_tokens, stream=True)
