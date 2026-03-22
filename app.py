import streamlit as st
from main import generate_agentic_response

# 1. Page Config
st.set_page_config(page_title="Mimo Agentic", page_icon="🤖", layout="wide")

# 2. Sidebar for Settings
with st.sidebar:
    st.title("⚙️ Agent Controls")
    temp = st.slider("Creativity (Temperature)", 0.0, 1.0, 0.7, 0.05)
    tokens = st.slider("Max Tokens", 64, 2048, 512, 32)
    agentic = st.checkbox("Enable Agentic Mode (ReAct style)", value=True)
    deep_think = st.checkbox("Enable Deep Thinking (Chain of Thought)", value=False)
    enable_exec = st.checkbox("Enable Code Execution (Sandbox)", value=False)
    yolo_mode = st.checkbox("YOLO Mode (Auto-fix errors)", value=False)

    if st.button("Clear Chat History"):
        st.session_state.messages = []
        st.experimental_rerun()

    st.markdown("---")
    st.info("System prompt is injected in Agentic Mode for reasoning and actions.")


# 3. Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []
if "terminal_output" not in st.session_state:
    st.session_state.terminal_output = ""

# 4. Main UI
st.title("🤖 Mimo Agentic Chat")
st.caption("Chat with a local Qwen2.5 model using session history + streaming output.")

# display history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# helper for structured rendering
import re

def render_response(full_text):
    parts = re.split(r"(```.*?```)", full_text, flags=re.S)
    for part in parts:
        if part.startswith("```") and part.rstrip().endswith("```"):
            inner = part.strip("`\n")
            if "\n" in inner:
                lang, code = inner.split("\n", 1)
            else:
                lang, code = "", ""
            st.code(code.rstrip("`\n"), language=lang.strip() or "python")
        elif part.strip():
            st.markdown(part)


# user input
user_prompt = st.chat_input("Ask the agent something (e.g., build, debug, explain)...")

def execute_code(code_block):
    raise NotImplementedError

if user_prompt:
    # Save user message
    st.session_state.messages.append({"role": "user", "content": user_prompt})

    with st.chat_message("user"):
        st.markdown(user_prompt)

    # Agent response
    with st.chat_message("assistant"):
        response_box = st.empty()
        output_text = ""
        try:
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

            # Handle execution if enabled
            if enable_exec:
                exec_matches = re.findall(r"<execute>(.*?)</execute>", output_text, re.S)
                if exec_matches:
                    for code_block in exec_matches:
                        exec_result = execute_code(code_block.strip())
                        st.session_state.terminal_output += f"\n>>> {code_block.strip()}\n{exec_result}\n"
                        # Append execution result to messages for next response
                        st.session_state.messages.append({
                            "role": "system",
                            "content": f"Code execution result:\n{exec_result}"
                        })
                        if yolo_mode:
                            # Auto-fix: generate new response with error
                            fix_stream = generate_agentic_response(
                                st.session_state.messages,
                                temperature=temp,
                                max_tokens=tokens,
                                stream=True,
                                chain_of_thought=deep_think,
                                enable_execution=enable_exec,
                            )
                            fix_text = ""
                            for token in fix_stream:
                                fix_text += token
                            output_text += "\n\nAuto-fix:\n" + fix_text
                            st.session_state.messages.append({"role": "assistant", "content": fix_text})

            # Render nicely with code block parsing
            response_box.empty()
            if deep_think:
                final_match = re.search(r"Final Answer:\\s*", output_text, flags=re.I)
                if final_match:
                    cot_text = output_text[: final_match.start()].strip()
                    answer_text = output_text[final_match.start() :].strip()

                    if cot_text:
                        with st.expander("Chain of Thought (Deep Thinking)", expanded=True):
                            st.markdown(cot_text)

                    render_response(answer_text)
                else:
                    render_response(output_text)
            else:
                render_response(output_text)

            # Save assistant response
            st.session_state.messages.append({"role": "assistant", "content": output_text})

        except Exception as err:
            st.error(f"Generation failed: {err}")

# Terminal View
st.markdown("---")
with st.expander("🖥️ Terminal Output (Code Executions)", expanded=False):
    st.code(st.session_state.terminal_output or "No executions yet.", language="text")


