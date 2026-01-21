"""
FastAPI Backend Module - MULTIMODAL VERSION
Handles image uploads and analysis
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import uuid
import os
import shutil
from pathlib import Path

from app.graph_compiler import compile_graph
from app.helpers import RCAState

# FastAPI app
api_app = FastAPI(title="RCA Analysis API - Multimodal", version="2.0.0")

# Global storage for sessions
sessions: Dict[str, Dict[str, Any]] = {}

# Compiled graph (loaded once)
rca_graph = None

# Directory for uploaded images
UPLOAD_DIR = Path("uploaded_images")
UPLOAD_DIR.mkdir(exist_ok=True)

class StartAnalysisRequest(BaseModel):
    problem: str

class AnswerRequest(BaseModel):
    session_id: str
    answer: str
    improved_answer: Optional[str] = None

class GenerateReportRequest(BaseModel):
    session_id: str

class SessionResponse(BaseModel):
    session_id: str
    current_question: Optional[str] = None
    why_no: int
    needs_improvement: bool = False
    improvement_suggestion: Optional[str] = None
    image_requested: bool = False  # NEW: Flag when system requests image
    completed: bool = False
    root_cause_extracted: bool = False
    root_cause: Optional[str] = None
    report: Optional[str] = None
    confidence_score: Optional[float] = None
    report_file: Optional[str] = None
    uploaded_images: List[str] = []
    image_analysis: Optional[str] = None

@api_app.on_event("startup")
async def startup_event():
    """Load model and compile graph on startup"""
    global rca_graph
    from app.model_loading import load_model
    
    print("Starting up FastAPI server (Multimodal)...")
    load_model()
    rca_graph = compile_graph()
    print("FastAPI server ready with image upload support!")

@api_app.post("/start", response_model=SessionResponse)
async def start_analysis(request: StartAnalysisRequest):
    """Start a new RCA analysis session"""
    session_id = str(uuid.uuid4())
    
    # Initialize state
    state: RCAState = {
        "problem": request.problem,
        "why_no": 0,
        "whys": [],
        "root_cause": "",
        "confidence_score": 0.0,
        "report": "",
        "user_input": "",
        "needs_validation": False,
        "retry_count": 0,
        "current_question": "",
        "needs_improvement": False,
        "improvement_suggestion": "",
        "improved_input": "",
        "early_root_cause_found": False,
        "uploaded_images": [],
        "current_image": None,
        "image_requested": False
    }
    
    from app.node_definitions import why_asker
    state = why_asker(state)
    
    sessions[session_id] = {
        "state": state,
        "completed": False
    }
    
    return SessionResponse(
        session_id=session_id,
        current_question=state.get("current_question"),
        why_no=state["why_no"],
        needs_improvement=False,
        uploaded_images=[]
    )

@api_app.post("/upload_image/{session_id}")
async def upload_image(session_id: str, file: UploadFile = File(...)):
    """
    Upload an image for the current Why question
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Validate file type
    allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid file type. Only JPEG, PNG, WEBP allowed.")
    
    # Save file
    file_ext = file.filename.split(".")[-1]
    safe_filename = f"{session_id}_{uuid.uuid4().hex[:8]}.{file_ext}"
    file_path = UPLOAD_DIR / safe_filename
    
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Update session state
    session = sessions[session_id]
    state = session["state"]
    
    state["uploaded_images"].append(str(file_path))
    state["current_image"] = str(file_path)
    
    return {
        "filename": safe_filename,
        "path": str(file_path),
        "message": "Image uploaded successfully. It will be analyzed when you submit your answer."
    }

@api_app.post("/answer", response_model=SessionResponse)
async def submit_answer(request: AnswerRequest):
    """Submit an answer (with optional image) and get next question or root cause"""
    if request.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[request.session_id]
    state = session["state"]
    
    state["user_input"] = request.answer
    if request.improved_answer:
        state["improved_input"] = request.improved_answer
    
    from app.node_definitions import answer_validator, why_asker, root_cause_extractor
    from app.graph_builder import should_continue_or_validate
    
    # Validate (will analyze image if available)
    state = answer_validator(state)
    
    # Extract image analysis from the last "why" entry
    image_analysis = None
    if state["whys"]:
        last_why = state["whys"][-1]
        image_analysis = last_why.get("image_analysis")
    
    # Clear current image after validation
    state["current_image"] = None
    
    # Improvement check
    if state.get("needs_improvement", False) and not request.improved_answer:
        return SessionResponse(
            session_id=request.session_id,
            current_question=state.get("current_question"),
            why_no=state["why_no"],
            needs_improvement=True,
            improvement_suggestion=state.get("improvement_suggestion"),
            image_requested=state.get("image_requested", False),
            completed=False,
            uploaded_images=state.get("uploaded_images", []),
            image_analysis=image_analysis
        )
    
    next_step = should_continue_or_validate(state)
    
    if next_step == "continue":
        state = why_asker(state)
        session["state"] = state
        return SessionResponse(
            session_id=request.session_id,
            current_question=state.get("current_question"),
            why_no=state["why_no"],
            needs_improvement=False,
            completed=False,
            uploaded_images=state.get("uploaded_images", []),
            image_analysis=image_analysis
        )
    
    elif next_step == "extract":
        state = root_cause_extractor(state)
        session["state"] = state
        
        return SessionResponse(
            session_id=request.session_id,
            current_question=None,
            why_no=state["why_no"],
            needs_improvement=False,
            completed=False,
            root_cause_extracted=True,
            root_cause=state["root_cause"],
            uploaded_images=state.get("uploaded_images", []),
            image_analysis=image_analysis
        )
    
    return SessionResponse(
        session_id=request.session_id,
        why_no=state["why_no"],
        uploaded_images=state.get("uploaded_images", []),
        image_analysis=image_analysis
    )

@api_app.post("/generate_report", response_model=SessionResponse)
async def generate_report_endpoint(request: GenerateReportRequest):
    """Generate final report after root cause extraction"""
    if request.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
        
    session = sessions[request.session_id]
    state = session["state"]
    
    from app.node_definitions import report_generator
    
    state = report_generator(state)
    session["state"] = state
    session["completed"] = True
    
    return SessionResponse(
        session_id=request.session_id,
        why_no=state["why_no"],
        completed=True,
        root_cause_extracted=True,
        root_cause=state["root_cause"],
        report=state["report"],
        confidence_score=state["confidence_score"],
        report_file="rca_report.md",
        uploaded_images=state.get("uploaded_images", [])
    )

@api_app.get("/report/{session_id}")
async def get_report(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    session = sessions[session_id]
    state = session["state"]
    return {
        "report": state.get("report", ""),
        "confidence_score": state.get("confidence_score", 0.0),
        "root_cause": state.get("root_cause", ""),
        "report_file": "rca_report.md",
        "uploaded_images": state.get("uploaded_images", [])
    }

@api_app.delete("/cleanup/{session_id}")
async def cleanup_session(session_id: str):
    """Clean up uploaded images for a session"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    state = session["state"]
    
    # Delete uploaded images
    for img_path in state.get("uploaded_images", []):
        if os.path.exists(img_path):
            os.remove(img_path)
    
    # Remove session
    del sessions[session_id]
    
    return {"message": "Session cleaned up successfully"}

@api_app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "model_loaded": rca_graph is not None,
        "multimodal": True
    }