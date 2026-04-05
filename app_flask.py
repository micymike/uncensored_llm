"""
app.py - Flask web application for Mimo AI with OpenAI-compatible API

This replaces the Streamlit app with a Flask-based solution:
- Serves HTML/CSS/JS frontend
- Provides OpenAI-compatible API endpoints
- Single deployment with both UI and API
"""

import os
import json
import time
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

# Import Mimo's existing functionality
from main import get_llm, generate_agentic_response, _rag_context, _build_system

# ─── Flask App Setup ───────────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("MimoFlask")

# ─── API Helper Functions ─────────────────────────────────────────────────────

def generate_response_id() -> str:
    """Generate a unique response ID in OpenAI format."""
    return f"chatcmpl-{int(time.time())}-{hash(str(time.time())) % 10000:04d}"

def estimate_tokens(text: str) -> int:
    """Rough token estimation."""
    return len(text.split()) * 1.3

# ─── API Routes ────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Serve the main chat interface."""
    return render_template("index.html")

@app.route("/api/v1/health")
def api_health():
    """Health check endpoint."""
    try:
        llm = get_llm()
        return jsonify({
            "status": "healthy",
            "model_loaded": True,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route("/api/v1/models")
def api_models():
    """List available models."""
    return jsonify({
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
    })

@app.route("/api/v1/chat/completions", methods=["POST"])
def api_chat_completions():
    """Chat completions endpoint - OpenAI compatible."""
    try:
        # Get request data
        request_data = request.get_json()
        if not request_data:
            return jsonify({
                "error": {
                    "message": "No request body provided",
                    "type": "invalid_request_error",
                    "code": "missing_request_body"
                }
            }), 400
        
        # Validate required fields
        if "messages" not in request_data:
            return jsonify({
                "error": {
                    "message": "Missing 'messages' field",
                    "type": "invalid_request_error",
                    "code": "missing_messages"
                }
            }), 400
        
        # Convert to Mimo format
        messages = [
            {"role": msg["role"], "content": msg["content"]} 
            for msg in request_data["messages"]
        ]
        
        # Get RAG context
        rag_ctx = None
        if messages and messages[-1].get("role") == "user":
            query = messages[-1].get("content", "")
            if query.strip():
                rag_ctx = _rag_context(query, k=3)
        
        # Build system prompt
        system_content = _build_system(False, rag_ctx)
        
        # Ensure system message is first
        if messages and messages[0].get("role") != "system":
            messages.insert(0, {"role": "system", "content": system_content})
        elif messages:
            messages[0]["content"] = system_content
        
        # Generate response
        response_id = generate_response_id()
        created_time = int(time.time())
        
        # Estimate tokens
        prompt_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])
        prompt_tokens = int(estimate_tokens(prompt_text))
        
        # Generate completion
        completion_text = ""
        token_count = 0
        
        for token in generate_agentic_response(
            messages=messages,
            temperature=request_data.get("temperature", 0.7),
            max_tokens=request_data.get("max_tokens", 1024),
            stream=True,
            enable_execution=False,
            rag_k=3
        ):
            if token.startswith("\x00STATS:"):
                continue
            completion_text += token
            token_count += 1
        
        completion_tokens = token_count
        
        return jsonify({
            "id": response_id,
            "object": "chat.completion",
            "created": created_time,
            "model": request_data.get("model", "mimo"),
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": completion_text},
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens
            }
        })
        
    except Exception as e:
        logger.error(f"Chat completion failed: {e}")
        return jsonify({
            "error": {
                "message": f"Generation failed: {e}",
                "type": "generation_error",
                "code": "internal_error"
            }
        }), 500

@app.route("/api/v1/chat/stream", methods=["POST"])
def api_chat_stream():
    """Streaming chat endpoint."""
    try:
        request_data = request.get_json()
        if not request_data or "messages" not in request_data:
            return jsonify({"error": "Invalid request"}), 400
        
        # Convert to Mimo format
        messages = [
            {"role": msg["role"], "content": msg["content"]} 
            for msg in request_data["messages"]
        ]
        
        # Get RAG context
        rag_ctx = None
        if messages and messages[-1].get("role") == "user":
            query = messages[-1].get("content", "")
            if query.strip():
                rag_ctx = _rag_context(query, k=3)
        
        # Build system prompt
        system_content = _build_system(False, rag_ctx)
        
        # Ensure system message is first
        if messages and messages[0].get("role") != "system":
            messages.insert(0, {"role": "system", "content": system_content})
        elif messages:
            messages[0]["content"] = system_content
        
        def generate():
            response_id = generate_response_id()
            created_time = int(time.time())
            
            # Send initial chunk
            yield f"data: {json.dumps({
                'id': response_id,
                'object': 'chat.completion.chunk',
                'created': created_time,
                'model': 'mimo',
                'choices': [{'index': 0, 'delta': {'role': 'assistant'}, 'finish_reason': None}]
            })}\n\n"
            
            # Stream content
            for token in generate_agentic_response(
                messages=messages,
                temperature=request_data.get("temperature", 0.7),
                max_tokens=request_data.get("max_tokens", 1024),
                stream=True,
                enable_execution=False,
                rag_k=3
            ):
                if token.startswith("\x00STATS:"):
                    continue
                yield f"data: {json.dumps({
                    'id': response_id,
                    'object': 'chat.completion.chunk',
                    'created': created_time,
                    'model': 'mimo',
                    'choices': [{'index': 0, 'delta': {'content': token}, 'finish_reason': None}]
                })}\n\n"
            
            # Send final chunk
            yield f"data: {json.dumps({
                'id': response_id,
                'object': 'chat.completion.chunk',
                'created': created_time,
                'model': 'mimo',
                'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'stop'}]
            })}\n\n"
            yield "data: [DONE]\n\n"
        
        from flask import Response
        return Response(generate(), mimetype='text/plain')
        
    except Exception as e:
        logger.error(f"Stream failed: {e}")
        return jsonify({"error": str(e)}), 500

# ─── Legacy Streamlit Compatibility Routes ───────────────────────────────────────

@app.route("/?api=v1&endpoint=health")
def legacy_health():
    """Legacy health endpoint for Streamlit compatibility."""
    return api_health()

@app.route("/?api=v1&endpoint=models")
def legacy_models():
    """Legacy models endpoint for Streamlit compatibility."""
    return api_models()

@app.route("/?api=v1&endpoint=chat/completions", methods=["POST"])
def legacy_chat_completions():
    """Legacy chat completions endpoint for Streamlit compatibility."""
    return api_chat_completions()

# ─── Run Application ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🧠 Mimo Flask Application Starting...")
    print("🌐 Web UI: http://localhost:5000")
    print("📡 API Health: http://localhost:5000/api/v1/health")
    print("📡 API Models: http://localhost:5000/api/v1/models")
    print("📡 API Chat: http://localhost:5000/api/v1/chat/completions")
    print("\n💡 Cline Configuration:")
    print('   API Base URL: http://localhost:5000/api/v1')
    print('   API Key: any-string (not validated)')
    print('   Model: mimo')
    
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
