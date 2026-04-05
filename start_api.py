"""
start_api.py - Simple startup script for Mimo API server
"""

import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    import api_server
    print("🚀 Starting Mimo API Server...")
    api_server.main() if hasattr(api_server, 'main') else None
