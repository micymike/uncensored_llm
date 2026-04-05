#!/usr/bin/env python3
"""
Production startup script for Mimo Flask Application
Optimized for memory efficiency and worker management
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def main():
    """Main production startup function."""
    
    # Set production environment variables
    os.environ.update({
        "LLAMA_N_CTX": "2048",  # Reduce context size to save memory
        "LLAMA_N_THREADS": "4",  # Optimize thread count
        "FLASK_ENV": "production",
        "PYTHONUNBUFFERED": "1",
        "PYTHONPATH": str(Path(__file__).parent)
    })
    
    print("🚀 Mimo Production Server Starting...")
    print("📊 Memory Optimization Enabled")
    print("🌐 Port: 8501")
    
    # Gunicorn configuration for memory optimization
    gunicorn_cmd = [
        "gunicorn",
        "--workers", "1",  # Single worker to prevent multiple model loads
        "--worker-class", "sync",
        "--worker-connections", "10",
        "--max-requests", "100",  # Restart worker after 100 requests
        "--max-requests-jitter", "10",
        "--timeout", "300",  # Longer timeout for model loading
        "--keep-alive", "2",
        "--bind", "0.0.0.0:8501",
        "--access-logfile", "-",
        "--error-logfile", "-",
        "--log-level", "info",
        "--preload",  # Load app before forking workers
        "app:app"
    ]
    
    try:
        # Start gunicorn
        print("🔄 Starting Gunicorn server...")
        subprocess.run(gunicorn_cmd, check=True)
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"❌ Server failed with exit code {e.returncode}")
        sys.exit(e.returncode)
    except FileNotFoundError:
        print("❌ Gunicorn not found. Install with: pip install gunicorn")
        sys.exit(1)

if __name__ == "__main__":
    main()
