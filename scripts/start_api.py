"""
Script to start the Customer Segmentation API
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Start the API with uvicorn"""
    
    # Determine script directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    # Change to project root
    os.chdir(project_root)
    
    # Set environment variables
    os.environ.setdefault("API_HOST", "127.0.0.1")
    os.environ.setdefault("API_PORT", "8000")
    
    host = os.getenv("API_HOST")
    port = os.getenv("API_PORT")
    
    print(f"🚀 Starting Customer Segmentation API on {host}:{port}")
    print(f"📊 Swagger UI available at: http://{host}:{port}/docs")
    print(f"📚 ReDoc available at: http://{host}:{port}/redoc")
    print(f"ℹ️  Custom docs at: http://{host}:{port}/docs-custom")
    print("\nPress Ctrl+C to stop the server\n")
    
    # Start uvicorn server
    cmd = [
        sys.executable, "-m", "uvicorn",
        "scripts.api:app",
        "--host", host,
        "--port", port,
        "--reload",
        "--log-level", "info"
    ]
    
    subprocess.run(cmd)

if __name__ == "__main__":
    main()
