"""
Helper Functions Module - MULTIMODAL VERSION
Extended to support image tracking
"""

from datetime import datetime
from typing import TypedDict, List, Optional


class RCAState(TypedDict):
    """State for RCA workflow - extended for multimodal support"""
    problem: str
    why_no: int
    whys: list[dict]
    root_cause: str
    confidence_score: float
    report: str
    user_input: str
    needs_validation: bool
    retry_count: int
    early_root_cause_found: bool
    current_question: str
    needs_improvement: bool
    improvement_suggestion: str
    improved_input: str
    
    # NEW FIELDS FOR MULTIMODAL
    uploaded_images: List[str]  # List of image paths uploaded in session
    current_image: Optional[str]  # Current image being processed
    image_requested: bool  # Flag when validator requests image evidence


def format_whys_context(whys: list[dict]) -> str:
    """Format previous whys for context - includes image indicators"""
    if not whys:
        return "No previous whys yet."
    
    context = ""
    for i, why in enumerate(whys, 1):
        context += f"Why {i}: {why['question']}\nAnswer: {why['answer']}"
        
        # Add image indicator if image was provided
        if why.get('has_image'):
            context += " [📷 Image evidence provided]"
        
        context += "\n\n"
    
    return context.strip()


def calculate_answer_quality_score(whys: list[dict]) -> float:
    """Calculate average quality score - small bonus for image-backed answers"""
    if not whys:
        return 0.0
    
    total_score = 0.0
    for why in whys:
        base_score = why.get('quality_score', 3.0)
        
        # Small bonus for answers with visual evidence
        if why.get('has_image'):
            base_score = min(5.0, base_score + 0.3)
        
        total_score += base_score
    
    return (total_score / len(whys)) / 5.0 * 100


def export_report_to_markdown(state: RCAState, filename: str = "rca_report.md") -> str:
    """Export report to markdown - includes image references"""
    
    # Build image section if images were used
    image_section = ""
    if state.get("uploaded_images"):
        image_section = "\n## Visual Evidence\n"
        for i, img_path in enumerate(state["uploaded_images"], 1):
            image_section += f"{i}. `{img_path}`\n"
        image_section += "\n---\n"
    
    markdown_content = f"""# Root Cause Analysis Report
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Analysis Type:** {"Multimodal (Text + Vision)" if state.get("uploaded_images") else "Text-Only"}

## Problem Statement
{state['problem']}

---
{image_section}
{state['report']}

---

**Overall Confidence Score:** {state['confidence_score']:.1f}%
"""
    
    with open(filename, 'w') as f:
        f.write(markdown_content)
    
    return filename