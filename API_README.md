# Mimo API Server - OpenAI Compatible

This API server provides OpenAI-compatible endpoints for your Mimo model, allowing you to use it with Cline and other OpenAI-compatible tools.

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements_api.txt
   ```

2. **Start the server:**
   ```bash
   python api_server.py
   ```

3. **Server runs on:** `http://localhost:8000`

## Cline Configuration

In Cline, configure these settings:

- **API Base URL:** `http://localhost:8000/v1`
- **API Key:** `any-string` (not validated, but required)
- **Model:** `mimo`

## Available Endpoints

### Chat Completions
- **URL:** `/v1/chat/completions`
- **Method:** `POST`
- **Format:** Standard OpenAI chat completions

```json
{
  "model": "mimo",
  "messages": [
    {"role": "user", "content": "Hello, how are you?"}
  ],
  "temperature": 0.7,
  "max_tokens": 1024,
  "stream": false
}
```

### Health Check
- **URL:** `/health`
- **Method:** `GET`
- **Returns:** Server status and model availability

### Models List
- **URL:** `/v1/models`
- **Method:** `GET`
- **Returns:** Available models (currently just "mimo")

## Features

✅ **Full OpenAI Compatibility** - Works with any OpenAI-compatible client
✅ **Streaming Support** - Real-time response streaming
✅ **RAG Integration** - Uses your existing ChromaDB knowledge base
✅ **Error Handling** - Graceful error responses
✅ **CORS Support** - Works with web-based clients
✅ **Health Monitoring** - Built-in health checks

## Usage Examples

### Python Client
```python
import openai

client = openai.OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="any-string"
)

response = client.chat.completions.create(
    model="mimo",
    messages=[{"role": "user", "content": "Hello!"}]
)

print(response.choices[0].message.content)
```

### curl
```bash
curl -X POST "http://localhost:8000/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer any-string" \
  -d '{
    "model": "mimo",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

## Notes

- The server uses your existing Mimo model and RAG system
- Token limits are enforced (default 1024, max 2048)
- Streaming is supported for real-time responses
- API key is not validated but required for OpenAI compatibility

## Troubleshooting

1. **Model not loading:** Check your model path in environment variables
2. **Port conflicts:** Change port in `api_server.py` if 8000 is in use
3. **CORS issues:** The server allows all origins by default

## Performance

- **Startup time:** ~10-30 seconds (model loading)
- **Response time:** Depends on query complexity and token count
- **Memory usage:** Similar to running Mimo in Streamlit
