#!/usr/bin/env python3
"""
Startup script to run both backend and frontend
"""

import subprocess
import sys
import time
import os
import signal
import threading
from pathlib import Path

def run_backend():
    """Run the FastAPI backend"""
    print("🚀 Starting FastAPI backend...")
    try:
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "app:app", 
            "--host", "0.0.0.0", 
            "--port", "8000", 
            "--reload"
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Backend failed to start: {e}")
    except KeyboardInterrupt:
        print("\n🛑 Backend stopped")

def run_frontend():
    """Run the frontend server"""
    print("🌐 Starting frontend server...")
    time.sleep(2)  # Give backend time to start
    
    try:
        subprocess.run([
            sys.executable, "serve_frontend.py", 
            "--port", "3000"
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Frontend failed to start: {e}")
    except KeyboardInterrupt:
        print("\n🛑 Frontend stopped")

def setup_files():
    """Ensure all necessary files are in place"""
    frontend_dir = Path("frontend")
    frontend_dir.mkdir(exist_ok=True)
    
    # Check if index.html exists in frontend directory
    index_file = frontend_dir / "index.html"
    if not index_file.exists():
        print("📄 Creating frontend/index.html...")
        print("💡 Please copy the HTML content to frontend/index.html")
        print(f"   File should be created at: {index_file.absolute()}")
        return False
    
    return True

def main():
    """Main startup function"""
    print("🎯 Restaurant Reservation App Startup")
    print("=" * 50)
    
    # Setup files
    if not setup_files():
        print("\n❌ Setup incomplete. Please create the frontend files first.")
        return
    
    # Check if required files exist
    required_files = ["app.py", "parse_reservation.py", "book_opentable.py"]
    missing_files = [f for f in required_files if not Path(f).exists()]
    
    if missing_files:
        print(f"❌ Missing required files: {', '.join(missing_files)}")
        return
    
    print("✅ All required files found")
    print("\n🔧 Starting services...")
    print("   - Backend API: http://localhost:8000")
    print("   - Frontend: http://localhost:3000")
    print("   - API Docs: http://localhost:8000/docs")
    print("\n💡 Press Ctrl+C to stop all services")
    
    # Start backend in a separate thread
    backend_thread = threading.Thread(target=run_backend, daemon=True)
    backend_thread.start()
    
    # Start frontend in main thread
    try:
        run_frontend()
    except KeyboardInterrupt:
        print("\n👋 Shutting down all services...")

if __name__ == "__main__":
    main()