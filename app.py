import streamlit as st
import re
import logging
from datetime import datetime
from main import generate_agentic_response, execute_code

# --- 1. Logging Configuration ---
# This ensures you see exactly what's happening in your SSH terminal/logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

# --- 2. Page Config ---
st.set_page_config(page_title="Mimo Agentic", page_icon="🤖", layout="wide")

# --- 3. Sidebar for Settings ---
with st.sidebar:
    st.title("⚙️ Agent Controls")
    temp = st.slider("Creativity (Temperature)", 0.0, 1.0, 0.7, 0.05)
    tokens = st.slider("Max Tokens", 64, 2048, 512, 32)
    
    st.markdown("---")
    agentic = st.checkbox("Enable Agentic Mode", value=True)
    deep_think = st.checkbox("Deep Thinking (CoT)", value=False)
    enable_exec = st.checkbox("Code Execution (Sandbox)", value=False)
    yolo_mode = st.checkbox("YOLO Mode (Auto-fix)", value=False)

    if st.button("Clear Chat History"):
        logging.info("User cleared chat history.")
        st.session_state.messages = []
        st.session_state.terminal_output = ""
        st.rerun()

    st.markdown("---")
    st.info("System: Model Qwen-3.5 Uncensored Q4_K_M")

# --- 4. Initialize session state ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "terminal_output" not in st.session_state:
    st.session_state.terminal_output = ""

# --- 5. UI Helper Functions ---
def render_response(full_text):
    """Parses text and code blocks for clean UI rendering."""
    parts = re.split(r"(```.*?```)", full_text, flags=re.S)
    for part in parts:
        if part.startswith("```") and part.rstrip().endswith("```"):
            inner = part.strip("`\n")
            if "\n" in inner:
                lang, code = inner.split("\n", 1)
            else:
                lang, code = "", inner
            st.code(code.rstrip("`\n"), language=lang.strip() or "python")
        elif part.strip():
            st.markdown(part)

# --- 6. Main UI ---
st.title("🤖 Mimo Agentic Chat")
st.caption(f"Status: Active | Device: CPU | RAM: ~8GB")

# Display history
for msg in st.session_state.messages:
    if msg["role"] != "system": # Hide system prompts from UI
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# User input
user_prompt = st.chat_input("Ask the agent something...")

if user_prompt:
    logging.info(f"USER QUERY: {user_prompt[:50]}...")
    st.session_state.messages.append({"role": "user", "content": user_prompt})

    with st.chat_message("user"):
        st.markdown(user_prompt)

    with st.chat_message("assistant"):
        response_box = st.empty()
        status_box = st.status("Thinking...", expanded=False)
        output_text = ""
        
        try:
            # Start streaming from LLM
            response_stream = generate_agentic_response(
                st.session_state.messages,
                temperature=temp,
                max_tokens=tokens,
                stream=True,
                chain_of_thought=deep_think,
                enable_execution=enable_exec,
            )

            for token in response_stream:
                output_text += token
                response_box.markdown(output_text + "▌")
            
            # 7. Code Execution Logic
            if enable_exec:
                exec_matches = re.findall(r"<execute>(.*?)</execute>", output_text, re.S)
                if exec_matches:
                    status_box.update(label="Executing Code...", state="running", expanded=True)
                    for code_block in exec_matches:
                        clean_code = code_block.strip()
                        logging.info(f"EXECUTING: {clean_code[:100]}")
                        
                        exec_result = execute_code(clean_code)
                        
                        # Update Terminal State
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        st.session_state.terminal_output += f"[{timestamp}] >>> {clean_code}\n{exec_result}\n\n"
                        
                        # Feed result back to model
                        st.session_state.messages.append({
                            "role": "system", 
                            "content": f"Code execution result:\n{exec_result}"
                        })

                        if yolo_mode:
                            status_box.update(label="Auto-fixing errors...", state="running")
                            fix_stream = generate_agentic_response(
                                st.session_state.messages,
                                temperature=temp,
                                max_tokens=tokens,
                                stream=True
                            )
                            fix_text = ""
                            for token in fix_stream:
                                fix_text += token
                            output_text += "\n\n**Auto-fix:**\n" + fix_text
            
            status_box.update(label="Response Complete", state="complete", expanded=False)
            
            # Final Clean Render
            response_box.empty()
            render_response(output_text)

            # Save assistant response
            st.session_state.messages.append({"role": "assistant", "content": output_text})
            logging.info("Response successfully generated.")

        except Exception as err:
            logging.error(f"STREAMING ERROR: {err}")
            st.error(f"Generation failed: {err}")

# 8. Terminal View (Bottom)
st.markdown("---")
with st.expander("🖥️ Terminal Output (Code Executions)", expanded=False):
    st.code(st.session_state.terminal_output or "No executions yet.", language="text")
