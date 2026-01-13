"""
Graph Builder Module
Exact copy from notebook: ROUTING LOGIC and GRAPH BUILDING sections
All routing logic and graph structure preserved as-is
"""

from langgraph.graph import StateGraph, END
from app.helpers import RCAState
from app.node_definitions import (
    why_asker,
    answer_validator,
    root_cause_extractor,
    report_generator
)


def should_continue_or_validate(state: RCAState) -> str:
    """Decide next node: validate answer or continue/extract - exact copy from notebook"""
    if state.get("needs_validation", False):
        return "validate"
    elif state["why_no"] < 5:
        return "continue"
    else:
        return "extract"


def build_graph() -> StateGraph:
    """
    Build the RCA graph exactly as defined in notebook
    Returns: Configured StateGraph (not compiled)
    """
    # Initialize graph
    workflow = StateGraph(RCAState)
    
    # Add nodes
    workflow.add_node("why_asker", why_asker)
    workflow.add_node("answer_validator", answer_validator)
    workflow.add_node("root_cause_extractor", root_cause_extractor)
    workflow.add_node("report_generator", report_generator)
    
    # Set entry point
    workflow.set_entry_point("why_asker")
    
    # Add conditional edges from why_asker
    workflow.add_conditional_edges(
        "why_asker",
        should_continue_or_validate,
        {
            "validate": "answer_validator",
            "continue": "why_asker",
            "extract": "root_cause_extractor"
        }
    )
    
    # Add conditional edges from answer_validator
    workflow.add_conditional_edges(
        "answer_validator",
        should_continue_or_validate,
        {
            "continue": "why_asker",
            "extract": "root_cause_extractor"
        }
    )
    
    # Add edge from root_cause_extractor to report_generator
    workflow.add_edge("root_cause_extractor", "report_generator")
    
    # Add edge from report_generator to END
    workflow.add_edge("report_generator", END)
    
    return workflow