"""
FastAPI Backend Module
Exposes the RCA graph as API endpoints for interactive execution
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uuid
import os

from app.graph_compiler import compile_graph
from app.helpers import RCAState

# FastAPI app
api_app = FastAPI(title="RCA Analysis API", version="1.0.0")

# Global storage for sessions
sessions: Dict[str, Dict[str, Any]] = {}

# Compiled graph (loaded once)
rca_graph = None

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
    completed: bool = False
    
    # New fields for split execution
    root_cause_extracted: bool = False
    root_cause: Optional[str] = None
    
    report: Optional[str] = None
    confidence_score: Optional[float] = None
    report_file: Optional[str] = None

@api_app.on_event("startup")
async def startup_event():
    """Load model and compile graph on startup"""
    global rca_graph
    from app.model_loading import load_model
    
    print("Starting up FastAPI server...")
    load_model()
    rca_graph = compile_graph()
    print("FastAPI server ready!")

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
        "early_root_cause_found": False  # NEW FIELD ADDED
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
        needs_improvement=False
    )

@api_app.post("/answer", response_model=SessionResponse)
async def submit_answer(request: AnswerRequest):
    """Submit an answer and get the next question OR the root cause"""
    if request.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[request.session_id]
    state = session["state"]
    
    state["user_input"] = request.answer
    if request.improved_answer:
        state["improved_input"] = request.improved_answer
    
    from app.node_definitions import answer_validator, why_asker, root_cause_extractor
    from app.graph_builder import should_continue_or_validate
    
    # Validate
    state = answer_validator(state)
    
    # Improvement check
    if state.get("needs_improvement", False) and not request.improved_answer:
        return SessionResponse(
            session_id=request.session_id,
            current_question=state.get("current_question"),
            why_no=state["why_no"],
            needs_improvement=True,
            improvement_suggestion=state.get("improvement_suggestion"),
            completed=False
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
            completed=False
        )
    
    elif next_step == "extract":
        # Only run extractor, pause before report generation
        state = root_cause_extractor(state)
        session["state"] = state
        
        return SessionResponse(
            session_id=request.session_id,
            current_question=None,
            why_no=state["why_no"],
            needs_improvement=False,
            completed=False,
            root_cause_extracted=True,
            root_cause=state["root_cause"]
        )
    
    return SessionResponse(session_id=request.session_id, why_no=state["why_no"])

@api_app.post("/generate_report", response_model=SessionResponse)
async def generate_report_endpoint(request: GenerateReportRequest):
    """Separate endpoint to generate report after root cause extraction"""
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
        report_file="rca_report.md"
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
        "report_file": "rca_report.md"
    }

@api_app.get("/health")
async def health_check():
    return {"status": "healthy", "model_loaded": rca_graph is not None}