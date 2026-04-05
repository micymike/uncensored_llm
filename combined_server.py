"""
combined_server.py - Runs both Streamlit UI and OpenAI-compatible API

This server allows you to run Mimo with both:
- Streamlit web UI (port 8501)
- OpenAI-compatible API (port 8000)

Usage:
    python combined_server.py
"""

import os
import sys
import threading
import time
import subprocess
import signal
from typing import Dict, List, Generator, Optional, Any

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ─── API Server Components ───────────────────────────────────────────────────
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from main import get_llm, _rag_context, _build_system

# ─── API Models ─────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str = Field(..., description="Message role: 'system', 'user', or 'assistant'")
    content: str = Field(..., description="Message content")

class ChatCompletionRequest(BaseModel):
    model: str = Field(default="mimo", description="Model name (ignored, always uses Mimo)")
    messages: List[ChatMessage] = Field(..., description="List of chat messages")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int = Field(default=1024, ge=1, le=2048, description="Maximum tokens to generate")
    stream: bool = Field(default=False, description="Enable streaming response")
    stop: Optional[List[str]] = Field(default=None, description="Stop sequences")

class ChatCompletionChoice(BaseModel):
    index: int
    message: Optional[Dict[str, Any]] = None
    delta: Optional[Dict[str, Any]] = None
    finish_reason: str

class UsageInfo(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: UsageInfo

# ─── FastAPI App ───────────────────────────────────────────────────────────
api_app = FastAPI(
    title="Mimo API",
    description="OpenAI-compatible API for Mimo AI Agent",
    version="1.0.0",
)

# CORS middleware for compatibility with various clients
api_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── API Helper Functions ───────────────────────────────────────────────────

def generate_response_id() -> str:
    """Generate a unique response ID in OpenAI format."""
    import time
    return f"chatcmpl-{int(time.time())}-{hash(str(time.time())) % 10000:04d}"

def estimate_tokens(text: str) -> int:
    """Rough token estimation."""
    return len(text.split()) * 1.3

# ─── API Endpoints ─────────────────────────────────────────────────────────

@api_app.get("/api/health")
async def api_health_check():
    """API health check endpoint."""
    try:
        llm = get_llm()
        return {
            "status": "healthy",
            "model_loaded": True,
            "service": "mimo-api"
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unavailable: {e}")

@api_app.get("/api/v1/models")
async def list_models():
    """List available models."""
    import time
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

@api_app.post("/api/v1/chat/completions")
async def create_chat_completion(request: ChatCompletionRequest):
    """Create chat completion."""
    import time
    import json
    
    try:
        # Convert messages to Mimo format
        mimo_messages = [
            {"role": msg.role, "content": msg.content} 
            for msg in request.messages
        ]
        
        # Get RAG context
        rag_ctx = None
        if mimo_messages and mimo_messages[-1].get("role") == "user":
            query = mimo_messages[-1].get("content", "")
            if query.strip():
                rag_ctx = _rag_context(query, k=3)
        
        # Build system prompt
        system_content = _build_system(False, rag_ctx)
        
        # Ensure system message is first
        if mimo_messages and mimo_messages[0].get("role") != "system":
            mimo_messages.insert(0, {"role": "system", "content": system_content})
        elif mimo_messages:
            mimo_messages[0]["content"] = system_content
        
        # Get model and generate response
        llm = get_llm()
        response_id = generate_response_id()
        created_time = int(time.time())
        
        # Estimate prompt tokens
        prompt_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in mimo_messages])
        prompt_tokens = int(estimate_tokens(prompt_text))
        
        if request.stream:
            return StreamingChatCompletionResponse(
                response_id=response_id,
                model=request.model,
                messages=mimo_messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                stop=request.stop,
                prompt_tokens=prompt_tokens
            )
        else:
            # Non-streaming response
            completion_text = ""
            token_count = 0
            
            response = llm.create_chat_completion(
                messages=mimo_messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                stream=False,
                stop=request.stop or ["</s>", "<|im_end|>"],
            )
            
            for chunk in response:
                delta = chunk.get("choices", [{}])[0].get("delta", {})
                token = delta.get("content", "")
                if token:
                    completion_text += token
                    token_count += 1
            
            completion_tokens = token_count
            
            return ChatCompletionResponse(
                id=response_id,
                created=created_time,
                model=request.model,
                choices=[
                    ChatCompletionChoice(
                        index=0,
                        message={"role": "assistant", "content": completion_text},
                        finish_reason="stop"
                    )
                ],
                usage=UsageInfo(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens
                )
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {e}")

class StreamingChatCompletionResponse:
    """Server-sent events streaming response."""
    
    def __init__(self, response_id: str, model: str, messages: List[Dict], 
                 temperature: float, max_tokens: int, stop: Optional[List[str]], 
                 prompt_tokens: int):
        self.response_id = response_id
        self.model = model
        self.messages = messages
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.stop = stop
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = 0
    
    async def __call__(self):
        """Async generator for streaming response."""
        try:
            llm = get_llm()
            
            response = llm.create_chat_completion(
                messages=self.messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=True,
                stop=self.stop or ["</s>", "<|im_end|>"],
            )
            
            # Send initial chunk
            yield self.format_chunk({
                "id": self.response_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": self.model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"role": "assistant"},
                        "finish_reason": None
                    }
                ]
            })
            
            # Stream content
            for chunk in response:
                delta = chunk.get("choices", [{}])[0].get("delta", {})
                token = delta.get("content", "")
                if token:
                    self.completion_tokens += 1
                    yield self.format_chunk({
                        "id": self.response_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": self.model,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {"content": token},
                                "finish_reason": None
                            }
                        ]
                    })
            
            # Send final chunk
            yield self.format_chunk({
                "id": self.response_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": self.model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop"
                    }
                ],
                "usage": {
                    "prompt_tokens": self.prompt_tokens,
                    "completion_tokens": self.completion_tokens,
                    "total_tokens": self.prompt_tokens + self.completion_tokens
                }
            })
            
        except Exception as e:
            yield self.format_chunk({
                "error": {"message": str(e), "type": "generation_error"}
            })
    
    def format_chunk(self, data: Dict) -> str:
        """Format data as server-sent event."""
        import json
        return f"data: {json.dumps(data)}\n\n"

# ─── Server Management ───────────────────────────────────────────────────────

class CombinedServer:
    """Manages both Streamlit and API servers."""
    
    def __init__(self):
        self.api_process = None
        self.streamlit_process = None
        self.running = True
    
    def start_api_server(self):
        """Start the FastAPI server."""
        print("🚀 Starting API server on port 8000...")
        uvicorn.run(
            api_app,
            host="0.0.0.0",
            port=8000,
            log_level="warning",  # Reduce log noise
            access_log=False
        )
    
    def start_streamlit_server(self):
        """Start the Streamlit server."""
        print("🎨 Starting Streamlit server on port 8501...")
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "app.py",
            "--server.port", "8501",
            "--server.address", "0.0.0.0",
            "--server.headless", "true",
            "--browser.gatherUsageStats", "false"
        ])
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        print("\n🛑 Shutting down servers...")
        self.running = False
        if self.api_process:
            self.api_process.terminate()
        if self.streamlit_process:
            self.streamlit_process.terminate()
        sys.exit(0)
    
    def run(self):
        """Run both servers."""
        # Register signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        print("🧠 Mimo Combined Server Starting...")
        print("📡 API: http://localhost:8000/api/v1/chat/completions")
        print("🎨 UI: http://localhost:8501")
        print("💡 Cline config: API Base URL = http://localhost:8000/api/v1")
        print("\nPress Ctrl+C to stop both servers\n")
        
        # Start API server in thread
        api_thread = threading.Thread(target=self.start_api_server, daemon=True)
        api_thread.start()
        
        # Give API server time to start
        time.sleep(2)
        
        try:
            # Start Streamlit server (this will block)
            self.start_streamlit_server()
        except KeyboardInterrupt:
            self.signal_handler(None, None)

if __name__ == "__main__":
    server = CombinedServer()
    server.run()
