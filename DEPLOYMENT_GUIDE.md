# Mimo API Integration Guide

## 🎯 Goal
Add OpenAI-compatible API endpoints to your existing Mimo deployment at `https://ai.uniconnect-learninghub.co.ke/`

## 📁 Files Modified/Created
- ✅ `streamlit_api.py` - New API module
- ✅ `app.py` - Updated to include API handling
- ✅ `api_server.py` - Standalone server (backup option)

## 🚀 Deployment Steps

### 1. Update Your Files
Make sure these files are in your deployment:
- `app.py` (updated)
- `streamlit_api.py` (new)
- `main.py` (existing)
- All other existing files

### 2. Deploy to Your VPS
```bash
git add .
git commit -m "Add OpenAI-compatible API endpoints"
git push
```

### 3. API Endpoints Available
Once deployed, these endpoints will be available:

#### Base URL: `https://ai.uniconnect-learninghub.co.ke`

- **Health Check:** `/?api=v1&endpoint=health`
- **Models List:** `/?api=v1&endpoint=models`
- **Chat Completions:** `/?api=v1&endpoint=chat/completions` (POST)

## 🔧 Cline Configuration

In Cline, set these parameters:

- **API Base URL:** `https://ai.uniconnect-learninghub.co.ke`
- **API Key:** `any-string` (not validated, but required)
- **Model:** `mimo`
- **Custom Endpoint Path:** `?api=v1&endpoint=chat/completions`

## 📝 Usage Examples

### Test Health Check
```bash
curl "https://ai.uniconnect-learninghub.co.ke/?api=v1&endpoint=health"
```

### Test Models
```bash
curl "https://ai.uniconnect-learninghub.co.ke/?api=v1&endpoint=models"
```

### Chat Completion (Cline Compatible)
```bash
curl -X POST "https://ai.uniconnect-learninghub.co.ke/?api=v1&endpoint=chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer any-key" \
  -d '{
    "model": "mimo",
    "messages": [{"role": "user", "content": "Hello, how are you?"}]
  }'
```

### Python Client
```python
import openai

client = openai.OpenAI(
    base_url="https://ai.uniconnect-learninghub.co.ke",
    api_key="any-string"
)

response = client.chat.completions.create(
    model="mimo",
    messages=[{"role": "user", "content": "Hello!"}]
)

print(response.choices[0].message.content)
```

## 🎯 Benefits

✅ **Single URL** - Both UI and API at the same domain
✅ **No Extra Ports** - Uses existing Streamlit deployment
✅ **Cline Compatible** - Works with OpenAI-compatible tools
✅ **RAG Integration** - Uses your existing knowledge base
✅ **Zero Downtime** - Updates alongside your regular app

## 🔍 How It Works

1. **API Detection**: The app checks for `?api=v1` in query parameters
2. **Routing**: If API request detected, handles it and stops UI rendering
3. **Normal Flow**: If not API request, shows regular Streamlit UI
4. **Same Model**: Uses your existing Mimo model and RAG system

## 🚨 Important Notes

- The API uses query parameters instead of path routing (Streamlit limitation)
- POST requests may have limitations on some Streamlit hosting platforms
- API key is not validated but required for OpenAI compatibility
- Both UI and API share the same model instance

## 🔄 Alternative: Standalone Server

If the Streamlit integration has issues, use the standalone server:

```bash
python api_server.py
# Runs on http://localhost:8000
```

Then configure Cline with:
- **API Base URL:** `http://localhost:8000/v1`
- **Model:** `mimo`

## 📊 Monitoring

Check API health: `https://ai.uniconnect-learninghub.co.ke/?api=v1&endpoint=health`

This will show:
- Model loading status
- Service health
- Timestamp

## 🎉 Ready to Use

Once deployed, you can use Mimo in:
- ✅ Cline AI assistant
- ✅ Custom Python applications
- ✅ OpenAI-compatible tools
- ✅ Web applications
- ✅ Any OpenAI client library
