"""
api_server.py - OpenAI-compatible API server for Mimo model

Provides standard OpenAI chat completions endpoint that works with:
- Cline AI assistant
- OpenAI client libraries
- Any OpenAI-compatible tool

Usage:
    python api_server.py
    # Server runs on http://localhost:8000
    # Endpoint: /v1/chat/completions
"""

import os
import sys
import time
import logging
from typing import List, Dict, Generator, Optional, Any
from datetime import datetime

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Import Mimo's existing functionality
from main import get_llm, _rag_context, _build_system

# ─── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("MimoAPI")

# ─── FastAPI App ───────────────────────────────────────────────────────────
app = FastAPI(
    title="Mimo API",
    description="OpenAI-compatible API for Mimo AI Agent",
    version="1.0.0",
)

# CORS middleware for compatibility with various clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── OpenAI-compatible Models ────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str = Field(..., description="Message role: 'system', 'user', or 'assistant'")
    content: str = Field(..., description="Message content")

class ChatCompletionRequest(BaseModel):
    model: str = Field(default="mimo", description="Model name (ignored, always uses Mimo)")
    messages: List[ChatMessage] = Field(..., description="List of chat messages")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int = Field(default=1024, ge=1, le=2048, description="Maximum tokens to generate")
    stream: bool = Field(default=False, description="Enable streaming response")
    top_p: float = Field(default=0.9, ge=0.0, le=1.0, description="Nucleus sampling (ignored)")
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0, description="Frequency penalty (ignored)")
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0, description="Presence penalty (ignored)")
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

# ─── Helper Functions ───────────────────────────────────────────────────────

def generate_response_id() -> str:
    """Generate a unique response ID in OpenAI format."""
    return f"chatcmpl-{int(time.time())}-{hash(str(time.time())) % 10000:04d}"

def estimate_tokens(text: str) -> int:
    """Rough token estimation (should be replaced with proper tokenizer)."""
    return len(text.split()) * 1.3  # Rough approximation

# ─── API Endpoints ─────────────────────────────────────────────────────────

@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "Mimo API",
        "version": "1.0.0",
        "description": "OpenAI-compatible API for Mimo AI Agent",
        "endpoints": {
            "chat_completions": "/v1/chat/completions",
            "models": "/v1/models",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Test model availability
        llm = get_llm()
        return {
            "status": "healthy",
            "model_loaded": True,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Service unavailable: {e}")

@app.get("/v1/models")
async def list_models():
    """List available models (OpenAI-compatible)."""
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

@app.post("/v1/chat/completions")
async def create_chat_completion(request: ChatCompletionRequest):
    """
    Create chat completion (OpenAI-compatible endpoint).
    
    This is the main endpoint that Cline and other OpenAI clients will use.
    """
    try:
        # Convert messages to Mimo format
        mimo_messages = [
            {"role": msg.role, "content": msg.content} 
            for msg in request.messages
        ]
        
        # Get RAG context if this is a user message
        rag_ctx = None
        if mimo_messages and mimo_messages[-1].get("role") == "user":
            query = mimo_messages[-1].get("content", "")
            if query.strip():
                rag_ctx = _rag_context(query, k=3)
        
        # Build system prompt
        system_content = _build_system(False, rag_ctx)  # No execution in API mode
        
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
        logger.error(f"Chat completion failed: {e}")
        raise HTTPException(status_code=500, detail=f"Generation failed: {e}")

class StreamingChatCompletionResponse:
    """Server-sent events streaming response for OpenAI compatibility."""
    
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
            logger.error(f"Streaming failed: {e}")
            yield self.format_chunk({
                "error": {"message": str(e), "type": "generation_error"}
            })
    
    def format_chunk(self, data: Dict) -> str:
        """Format data as server-sent event."""
        import json
        return f"data: {json.dumps(data)}\n\n"

# ─── Server Startup ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🧠 Mimo API Server Starting...")
    print("📡 OpenAI-compatible endpoint: http://localhost:8000/v1/chat/completions")
    print("🔍 Health check: http://localhost:8000/health")
    print("📋 Models list: http://localhost:8000/v1/models")
    print("\n💡 Usage in Cline:")
    print('   API Base URL: http://localhost:8000/v1')
    print('   API Key: any-string (not validated)')
    print('   Model: mimo')
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=True
    )
