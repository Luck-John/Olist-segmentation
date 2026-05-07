"""
Script to start the Customer Segmentation API
"""

import os
import sys
import subprocess
import socket
from pathlib import Path

def _is_port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.2)
        return s.connect_ex((host, port)) == 0


def _pick_port(host: str, preferred_port: int) -> int:
    port = preferred_port
    for _ in range(50):
        if not _is_port_in_use(host, port):
            return port
        port += 1
    return preferred_port


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
    port = int(os.getenv("API_PORT"))
    port = _pick_port(host, port)
    os.environ["API_PORT"] = str(port)
    
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
        "--proxy-headers",
        "--forwarded-allow-ips=*",
        "--reload",
        "--log-level", "info",
    ]
    
    subprocess.run(cmd)

if __name__ == "__main__":
    main()
