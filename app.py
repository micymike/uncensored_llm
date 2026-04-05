"""
app.py - Flask web application for Mimo AI with OpenAI-compatible API

This Flask app serves both the web UI and API endpoints:
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

# ─── Global Model Instance (Prevent Multiple Loading) ───────────────────────────
_model_instance = None
_model_lock = None

def get_global_model():
    """Get or create a single global model instance."""
    global _model_instance, _model_lock
    if _model_instance is None:
        if _model_lock is None:
            import threading
            _model_lock = threading.Lock()
        with _model_lock:
            if _model_instance is None:
                logger.info("Loading global model instance...")
                _model_instance = get_llm()
                logger.info("Global model instance loaded successfully")
    return _model_instance

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
    """Health check endpoint with memory optimization."""
    try:
        # Check if model is loaded without loading it
        if _model_instance is not None:
            model_status = True
            model_loaded = "loaded"
        else:
            # Quick check if we can load the model (but don't actually load it)
            model_path = os.getenv("LLAMA_MODEL_PATH", "Qwen3.5-9B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf")
            model_status = os.path.exists(model_path)
            model_loaded = "available" if model_status else "not_found"
        
        return jsonify({
            "status": "healthy",
            "model_loaded": model_loaded,
            "model_status": model_status,
            "timestamp": datetime.now().isoformat(),
            "memory_optimized": True
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
    """Chat completions endpoint - OpenAI compatible with memory optimization."""
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
        
        # Get RAG context (with error handling)
        rag_ctx = None
        try:
            if messages and messages[-1].get("role") == "user":
                query = messages[-1].get("content", "")
                if query.strip():
                    rag_ctx = _rag_context(query, k=3)
        except Exception as rag_error:
            logger.warning(f"RAG retrieval failed: {rag_error}")
            rag_ctx = None
        
        # Build system prompt
        system_content = _build_system(False, rag_ctx)
        
        # Ensure system message is first
        if messages and messages[0].get("role") != "system":
            messages.insert(0, {"role": "system", "content": system_content})
        elif messages:
            messages[0]["content"] = system_content
        
        # Generate response using global model
        response_id = generate_response_id()
        created_time = int(time.time())
        
        # Estimate tokens
        prompt_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])
        prompt_tokens = int(estimate_tokens(prompt_text))
        
        # Get global model instance
        model = get_global_model()
        
        # Generate completion with memory optimization
        completion_text = ""
        token_count = 0
        
        try:
            for token in generate_agentic_response(
                messages=messages,
                temperature=request_data.get("temperature", 0.7),
                max_tokens=min(request_data.get("max_tokens", 1024), 1536),  # Cap max tokens
                stream=True,
                enable_execution=False,
                rag_k=3
            ):
                if token.startswith("\x00STATS:"):
                    continue
                completion_text += token
                token_count += 1
                
                # Prevent infinite loops
                if token_count > 2048:
                    break
                    
        except Exception as gen_error:
            logger.error(f"Generation failed: {gen_error}")
            completion_text = f"I apologize, but I encountered an error while generating the response: {str(gen_error)}"
        
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

@app.route("/api/v1/execute", methods=["POST"])
def api_execute_code():
    """Execute code endpoint for runnable code blocks."""
    try:
        from main import execute_code
        
        request_data = request.get_json()
        if not request_data or "code" not in request_data:
            return jsonify({
                "error": {
                    "message": "Missing 'code' field",
                    "type": "invalid_request_error"
                }
            }), 400
        
        code = request_data["code"]
        language = request_data.get("language", "python")
        
        # Execute the code
        result = execute_code(code)
        
        return jsonify({
            "success": True,
            "output": result,
            "language": language
        })
        
    except Exception as e:
        logger.error(f"Code execution failed: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "output": f"Error: {e}"
        }), 500

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
    # Set production environment variables
    os.environ.setdefault("LLAMA_N_CTX", "2048")  # Reduce context size
    os.environ.setdefault("LLAMA_N_THREADS", "4")  # Optimize threads
    os.environ.setdefault("FLASK_ENV", "production")
    
    print("🧠 Mimo Flask Application Starting...")
    print("🌐 Web UI: http://localhost:8501")
    print("📡 API Health: http://localhost:8501/api/v1/health")
    print("📡 API Models: http://localhost:8501/api/v1/models")
    print("📡 API Chat: http://localhost:8501/api/v1/chat/completions")
    print("\n💡 Cline Configuration:")
    print('   API Base URL: http://localhost:8501/api/v1')
    print('   API Key: any-string (not validated)')
    print('   Model: mimo')
    print("\n🚀 Production Mode - Memory Optimized")
    
    # Check if running with gunicorn (production)
    if 'gunicorn' in sys.modules or os.getenv('GUNICORN_CMD_ARGS'):
        print("🔄 Running with Gunicorn - Pre-loading model...")
        get_global_model()
        print("✅ Model pre-loaded for production")
    else:
        print("⚠️  Development mode detected")
        print("💡 For production, use: gunicorn --workers 1 --timeout 300 app:app")
    
    # Flask development server (for testing only)
    app.run(
        host="0.0.0.0",
        port=8501,
        debug=False,  # Disable debug for production
        threaded=True,
        use_reloader=False  # Prevent multiple model loads
    )
