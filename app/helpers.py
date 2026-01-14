"""
Helper Functions Module
Exact copy from notebook: HELPER FUNCTIONS section
No modifications to logic or behavior
"""

from datetime import datetime
from typing import TypedDict


class RCAState(TypedDict):
    """State for RCA workflow - exact copy from notebook"""
    problem: str  # Initial problem description
    why_no: int  # Current why iteration (0-5)
    whys: list[dict]  # List of {question, answer} pairs
    root_cause: str  # Extracted root cause
    confidence_score: float  # Confidence in root cause (0-100)
    report: str  # Final RCA report
    user_input: str  # User's answer to current why
    needs_validation: bool  # Flag for answer validation
    retry_count: int  # Number of validation retries
    early_root_cause_found: bool  # NEW: Flag for systematic root cause detection at Why 4+


def format_whys_context(whys: list[dict]) -> str:
    """Format previous whys for context - exact copy from notebook"""
    if not whys:
        return "No previous whys yet."
    
    context = ""
    for i, why in enumerate(whys, 1):
        context += f"Why {i}: {why['question']}\nAnswer: {why['answer']}\n\n"
    return context.strip()


def calculate_answer_quality_score(whys: list[dict]) -> float:
    """Calculate average quality score of all answers - exact copy from notebook"""
    if not whys:
        return 0.0
    
    total_score = sum(why.get('quality_score', 3.0) for why in whys)
    return (total_score / len(whys)) / 5.0 * 100  # Convert to percentage


def export_report_to_markdown(state: RCAState, filename: str = "rca_report.md") -> str:
    """Export report to markdown file - exact copy from notebook"""
    markdown_content = f"""# Root Cause Analysis Report
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Problem Statement
{state['problem']}

---

{state['report']}

---

**Overall Confidence Score:** {state['confidence_score']:.1f}%
"""
    
    with open(filename, 'w') as f:
        f.write(markdown_content)
    
    return filename