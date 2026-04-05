"""
streamlit_api.py - API endpoints for Mimo that work with Streamlit

This file provides OpenAI-compatible endpoints that can be used alongside
your existing Streamlit app at the same URL.

Usage:
    Add this to your Streamlit deployment and access via:
    https://ai.uniconnect-learninghub.co.ke/api/v1/chat/completions
"""

import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Any

import streamlit as st

# Configure logging
logger = logging.getLogger("MimoAPI")

# API Models
class ChatMessage:
    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content

# API Helper Functions
def generate_response_id() -> str:
    """Generate a unique response ID in OpenAI format."""
    return f"chatcmpl-{int(time.time())}-{hash(str(time.time())) % 10000:04d}"

def estimate_tokens(text: str) -> int:
    """Rough token estimation."""
    return len(text.split()) * 1.3

def api_health_check() -> Dict:
    """Health check for API."""
    try:
        from main import get_llm
        llm = get_llm()
        return {
            "status": "healthy",
            "model_loaded": True,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

def api_list_models() -> Dict:
    """List available models."""
    return {
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
    }

def api_chat_completion(request_data: Dict) -> Dict:
    """Process chat completion request."""
    try:
        from main import generate_agentic_response, _rag_context, _build_system
        
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
        
        return {
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
        }
        
    except Exception as e:
        logger.error(f"Chat completion failed: {e}")
        return {
            "error": {
                "message": f"Generation failed: {e}",
                "type": "generation_error",
                "code": "internal_error"
            }
        }

def handle_api_request():
    """Main API request handler - call this at the top of your app.py"""
    
    # Check if this is an API request
    query_params = st.query_params
    
    # Check for API path
    if "api" in query_params and query_params["api"] == "v1":
        
        # Set response headers for API
        if hasattr(st, 'set_page_config'):
            try:
                st.set_page_config(page_title="Mimo API", layout="centered")
            except:
                pass
        
        # Handle different endpoints
        path_parts = []
        if "endpoint" in query_params:
            endpoint = query_params["endpoint"]
        else:
            # Try to get endpoint from URL path
            # This is a workaround since Streamlit doesn't provide direct path access
            endpoint = "info"
        
        if endpoint == "health":
            health = api_health_check()
            st.json(health)
            return True
        
        elif endpoint == "models":
            models = api_list_models()
            st.json(models)
            return True
        
        elif endpoint == "chat/completions":
            # Handle POST request
            if hasattr(st, 'request') and st.request:
                try:
                    # Get request body
                    if hasattr(st.request, 'get_json'):
                        request_body = st.request.get_json()
                    else:
                        # Fallback for Streamlit Cloud
                        # Try to get JSON from form data or other methods
                        request_body = {}
                    
                    if not request_body:
                        st.error("No request body provided")
                        return True
                    
                    response = api_chat_completion(request_body)
                    st.json(response)
                    return True
                    
                except Exception as e:
                    error_response = {
                        "error": {
                            "message": f"Request processing failed: {e}",
                            "type": "request_error",
                            "code": "bad_request"
                        }
                    }
                    st.json(error_response)
                    return True
            else:
                # Show usage info for GET requests
                usage = {
                    "message": "This endpoint accepts POST requests",
                    "usage": {
                        "method": "POST",
                        "headers": {
                            "Content-Type": "application/json",
                            "Authorization": "Bearer your-api-key"
                        },
                        "body": {
                            "model": "mimo",
                            "messages": [
                                {"role": "user", "content": "Your message here"}
                            ],
                            "temperature": 0.7,
                            "max_tokens": 1024
                        }
                    }
                }
                st.json(usage)
                return True
        
        else:
            # API info
            api_info = {
                "name": "Mimo API",
                "version": "1.0.0",
                "description": "OpenAI-compatible API for Mimo AI Agent",
                "base_url": "https://ai.uniconnect-learninghub.co.ke",
                "endpoints": {
                    "health": "/?api=v1&endpoint=health",
                    "models": "/?api=v1&endpoint=models", 
                    "chat_completions": "/?api=v1&endpoint=chat/completions"
                },
                "model": "mimo",
                "usage_examples": {
                    "curl": '''curl -X POST "https://ai.uniconnect-learninghub.co.ke/?api=v1&endpoint=chat/completions" \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer any-key" \\
  -d '{
    "model": "mimo",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'''
                }
            }
            st.json(api_info)
            return True
    
    return False

# Example usage in app.py:
# 
# At the top of your app.py file:
# 
# import streamlit as st
# from streamlit_api import handle_api_request
# 
# # Handle API requests first
# if handle_api_request():
#     st.stop()
# 
# # Then continue with your regular Streamlit UI
# st.title("🧠 Mimo · Agentic Chat")
# # ... rest of your app
