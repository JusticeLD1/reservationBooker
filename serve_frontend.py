#!/usr/bin/env python3
"""
Simple static file server for the frontend
Run this alongside your FastAPI backend
"""

import http.server
import socketserver
import os
import webbrowser
from pathlib import Path

class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(Path("frontend").absolute()), **kwargs)

    def end_headers(self):
        # Add CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

def serve_frontend(port=3000, open_browser=True):
    """Serve the frontend on the specified port"""
    
    # Create frontend directory if it doesn't exist
    frontend_dir = Path("frontend")
    frontend_dir.mkdir(exist_ok=True)
    
    # Create js directory if it doesn't exist
    js_dir = frontend_dir / "js"
    js_dir.mkdir(exist_ok=True)
    
    # Start server
    handler = CustomHTTPRequestHandler
    
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"🌐 Frontend server starting at http://localhost:{port}")
        print(f"📁 Serving files from: {frontend_dir.absolute()}")
        print("💡 Make sure your FastAPI backend is running on http://localhost:8000")
        print("\n🔧 To stop the server, press Ctrl+C")
        
        if open_browser:
            webbrowser.open(f"http://localhost:{port}")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n👋 Frontend server stopped")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Serve the frontend")
    parser.add_argument("--port", type=int, default=3000, help="Port to serve on (default: 3000)")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser automatically")
    
    args = parser.parse_args()
    
    serve_frontend(port=args.port, open_browser=not args.no_browser)