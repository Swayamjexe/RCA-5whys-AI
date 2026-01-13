"""
Main Entry Point
Starts FastAPI server and launches Gradio UI
Single command to run the entire RCA Analysis application
"""

import uvicorn
import threading
import time
from app.api import api_app
from app.gradio_ui import launch_gradio


def run_fastapi():
    """Run FastAPI server in background"""
    uvicorn.run(
        api_app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )


def main():
    """
    Main entry point
    Starts FastAPI backend and Gradio frontend
    """
    print("\n" + "="*60)
    print("🚀 STARTING RCA ANALYSIS APPLICATION")
    print("="*60)
    
    # Start FastAPI in background thread
    print("\n[1/2] Starting FastAPI backend server...")
    api_thread = threading.Thread(target=run_fastapi, daemon=True)
    api_thread.start()
    
    # Wait for FastAPI to be ready
    print("Waiting for FastAPI to initialize...")
    time.sleep(5)
    
    # Launch Gradio UI
    print("\n[2/2] Launching Gradio UI...")
    print("\n" + "="*60)
    print("✅ APPLICATION READY!")
    print("="*60)
    print("\n📱 Gradio UI: http://localhost:7860")
    print("🔌 FastAPI Backend: http://localhost:8000")
    print("📚 API Docs: http://localhost:8000/docs")
    print("\n" + "="*60)
    print("Press Ctrl+C to stop the application")
    print("="*60 + "\n")
    
    try:
        launch_gradio()
    except KeyboardInterrupt:
        print("\n\n" + "="*60)
        print("👋 Shutting down RCA Analysis Application")
        print("="*60)


if __name__ == "__main__":
    main()