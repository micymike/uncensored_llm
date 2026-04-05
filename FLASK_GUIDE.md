# Mimo Flask Application - Complete Guide

## 🎯 Overview
Flask-based web application with OpenAI-compatible API endpoints and modern web UI.

## 📁 File Structure
```
uncensored_llm/
├── app_flask.py              # Main Flask application
├── main.py                   # Mimo core functionality
├── requirements_flask.txt     # Python dependencies
├── templates/
│   └── index.html           # Web UI template
├── static/
│   └── js/
│       └── app.js           # Frontend JavaScript
└── rag.py                   # RAG functionality
```

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements_flask.txt
```

### 2. Run the Application
```bash
python app_flask.py
```

### 3. Access the Application
- **Web UI:** http://localhost:5000
- **API Health:** http://localhost:5000/api/v1/health
- **API Models:** http://localhost:5000/api/v1/models
- **API Chat:** http://localhost:5000/api/v1/chat/completions

## 🔧 API Endpoints

### Base URL: `http://localhost:5000/api/v1`

#### Health Check
```http
GET /api/v1/health
```

#### List Models
```http
GET /api/v1/models
```

#### Chat Completions
```http
POST /api/v1/chat/completions
Content-Type: application/json
Authorization: Bearer any-key

{
  "model": "mimo",
  "messages": [
    {"role": "user", "content": "Hello!"}
  ],
  "temperature": 0.7,
  "max_tokens": 1024
}
```

#### Streaming Chat
```http
POST /api/v1/chat/stream
Content-Type: application/json

{
  "model": "mimo",
  "messages": [
    {"role": "user", "content": "Hello!"}
  ]
}
```

## 🎨 Web UI Features

### Chat Interface
- **Modern Design:** Beautiful gradient background with glassmorphism effects
- **Real-time Chat:** Smooth messaging with typing indicators
- **Code Highlighting:** Syntax highlighting for code blocks
- **Responsive Layout:** Works on desktop and mobile

### Controls Panel
- **Temperature:** Adjust response creativity (0.0 - 1.0)
- **Max Tokens:** Control response length (64 - 2048)
- **RAG Depth:** Set knowledge retrieval depth (1 - 10)
- **Modes:** Toggle agentic mode and code execution

### Features
- **Export Chat:** Download conversation as JSON
- **Clear Chat:** Reset conversation history
- **Keyboard Shortcuts:** Ctrl+K (clear), Ctrl+E (export)
- **Live Stats:** Token count, response time, tokens/sec

## 🔗 Cline Integration

Configure Cline with these settings:

- **API Base URL:** `http://localhost:5000/api/v1`
- **API Key:** `any-string` (not validated)
- **Model:** `mimo`

## 🚀 Deployment

### Local Development
```bash
python app_flask.py
```

### Production Deployment (VPS)
```bash
# Install production server
pip install gunicorn

# Run with Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app_flask:app

# Or with systemd service
sudo systemctl enable mimo
sudo systemctl start mimo
```

### Docker Deployment
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements_flask.txt .
RUN pip install -r requirements_flask.txt

COPY . .
EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app_flask:app"]
```

### Cloud Deployment
The Flask app can be deployed on:
- **Heroku:** Simple Git-based deployment
- **Render:** Auto-deploy from GitHub
- **DigitalOcean App Platform:** Managed container hosting
- **AWS Elastic Beanstalk:** Scalable deployment
- **Google Cloud Run:** Serverless container hosting

## 🔄 Migration from Streamlit

### Advantages of Flask Solution:
✅ **Full API Control:** Complete OpenAI compatibility  
✅ **Better Performance:** Faster response times  
✅ **Modern UI:** Beautiful responsive interface  
✅ **Single Deployment:** UI and API together  
✅ **Production Ready:** Built for production use  

### Migration Steps:
1. **Backup existing files:** `cp app.py app_streamlit_backup.py`
2. **Install Flask dependencies:** `pip install -r requirements_flask.txt`
3. **Test locally:** `python app_flask.py`
4. **Update deployment:** Replace Streamlit with Flask
5. **Update DNS/Proxy:** Point to port 5000 instead of 8501

## 🛠️ Configuration

### Environment Variables
```bash
export LLAMA_MODEL_PATH="your_model.gguf"
export LLAMA_N_CTX="2048"
export LLAMA_N_THREADS="4"
export FLASK_ENV="production"
```

### Customization
- **UI Theme:** Modify CSS in `templates/index.html`
- **API Routes:** Add new endpoints in `app_flask.py`
- **Model Settings:** Update parameters in `main.py`

## 📊 Monitoring

### Health Monitoring
```bash
# Check application health
curl http://localhost:5000/api/v1/health

# Monitor logs
tail -f /var/log/mimo/app.log
```

### Performance Metrics
The application tracks:
- Response times
- Token usage
- Error rates
- Model loading status

## 🔒 Security

### Production Security
- **CORS:** Configured for specific origins
- **Input Validation:** Sanitized user inputs
- **Rate Limiting:** Can be added with Flask-Limiter
- **HTTPS:** Use reverse proxy (nginx/caddy) for SSL

## 🆘 Troubleshooting

### Common Issues
1. **Model not loading:** Check model path and permissions
2. **Port conflicts:** Change port in `app_flask.py`
3. **Memory issues:** Reduce context size or model quantization
4. **CORS errors:** Configure allowed origins

### Debug Mode
```bash
export FLASK_ENV=development
python app_flask.py
```

## 🎉 Success!

You now have a complete Flask-based Mimo application with:
- Beautiful web interface
- Full OpenAI-compatible API
- Production-ready deployment
- Easy Cline integration

The application runs on a single port (5000) and provides both UI and API functionality, making deployment much simpler than the Streamlit solution.
