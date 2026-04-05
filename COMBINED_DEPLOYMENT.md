# Combined Mimo Server Deployment

This setup allows you to run both the Streamlit UI and OpenAI-compatible API on the same deployment.

## Quick Start

1. **Install combined dependencies:**
   ```bash
   pip install -r requirements_combined.txt
   ```

2. **Run the combined server:**
   ```bash
   python combined_server.py
   ```

3. **Access both services:**
   - **Streamlit UI:** `http://localhost:8501`
   - **API Endpoint:** `http://localhost:8000/api/v1/chat/completions`

## Cline Configuration

Configure Cline to use your existing deployment:

- **API Base URL:** `http://your-domain.com/api/v1`
- **API Key:** `any-string` (not validated)
- **Model:** `mimo`

## Deployment Options

### Option 1: Local Development
```bash
python combined_server.py
```

### Option 2: Docker Deployment
Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements_combined.txt .
RUN pip install -r requirements_combined.txt

COPY . .
EXPOSE 8000 8501

CMD ["python", "combined_server.py"]
```

Build and run:
```bash
docker build -t mimo-combined .
docker run -p 8000:8000 -p 8501:8501 mimo-combined
```

### Option 3: Cloud Deployment (Heroku, Railway, etc.)
- Use `combined_server.py` as your entry point
- Expose ports 8000 and 8501
- Set environment variables for your model path

## API Endpoints

### Chat Completions
```
POST /api/v1/chat/completions
```

### Health Check
```
GET /api/health
```

### Models List
```
GET /api/v1/models
```

## URL Mapping

| Service | Local URL | Production URL |
|---------|-----------|----------------|
| Streamlit UI | http://localhost:8501 | https://your-domain.com |
| API Chat | http://localhost:8000/api/v1/chat/completions | https://your-domain.com/api/v1/chat/completions |
| API Health | http://localhost:8000/api/health | https://your-domain.com/api/health |

## Benefits

✅ **Single deployment** - No need for separate servers
✅ **Shared model** - Both services use the same loaded model
✅ **Same URL** - Use your existing domain
✅ **RAG integration** - Both UI and API use your knowledge base
✅ **Resource efficient** - One model instance serves both

## Migration from Existing Deployment

If you already have Mimo deployed:

1. **Replace your current startup command** with `python combined_server.py`
2. **Update Cline configuration** to point to `/api/v1` endpoint
3. **No changes needed** to your existing Streamlit UI

## Example Cline Setup

```
API Base URL: https://mimo-yourdomain.com/api/v1
API Key: sk-any-string
Model: mimo
```

## Testing

Test both services:

```bash
# Test API health
curl http://localhost:8000/api/health

# Test API chat
curl -X POST "http://localhost:8000/api/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{"model": "mimo", "messages": [{"role": "user", "content": "Hello!"}]}'

# Test Streamlit UI
# Open http://localhost:8501 in browser
```

## Troubleshooting

1. **Port conflicts:** Change ports in `combined_server.py`
2. **Model loading:** Ensure `LLAMA_MODEL_PATH` is set
3. **CORS issues:** API allows all origins by default
4. **Memory usage:** Monitor RAM usage with both services running

This approach gives you the best of both worlds - your existing Streamlit UI plus OpenAI API compatibility for Cline and other tools!
