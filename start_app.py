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
        # Set environment variables for database and security
        env = os.environ.copy()
        env["DATABASE_URL"] = os.getenv("DATABASE_URL", "sqlite:///./reservation_booker.db")
        env["SECRET_KEY"] = os.getenv("SECRET_KEY", "your-secret-key-here")  # Change in production!
        
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "app:app", 
            "--host", "0.0.0.0", 
            "--port", "8000", 
            "--reload"
        ], check=True, env=env)
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
    # Create frontend directory structure
    frontend_dir = Path("frontend")
    frontend_dir.mkdir(exist_ok=True)
    
    # Create js directory
    js_dir = frontend_dir / "js"
    js_dir.mkdir(exist_ok=True)
    
    # Check required frontend files
    required_files = [
        "index.html",
        "login.html",
        "register.html",
        "dashboard.html",
        "js/auth.js"
    ]
    
    missing_files = []
    for file in required_files:
        if not (frontend_dir / file).exists():
            missing_files.append(file)
    
    if missing_files:
        print("❌ Missing frontend files:")
        for file in missing_files:
            print(f"   - {file}")
        return False
    
    return True

def main():
    """Main startup function"""
    print("🎯 Restaurant Reservation App Startup")
    print("=" * 50)
    
    # Setup files
    if not setup_files():
        print("\n❌ Setup incomplete. Please create the missing frontend files first.")
        return
    
    # Check if required backend files exist
    required_files = [
        "app.py",
        "parse_reservation.py",
        "reservationStream/book_opentable.py",
        "database.py",
        "auth.py"
    ]
    missing_files = [f for f in required_files if not Path(f).exists()]
    
    if missing_files:
        print(f"❌ Missing required backend files: {', '.join(missing_files)}")
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