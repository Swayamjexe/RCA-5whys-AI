"""
Graph Compiler Module
Compiles the graph with the same execution behavior as notebook
"""

from app.graph_builder import build_graph


def compile_graph():
    """
    Compile the RCA graph exactly as in notebook
    Returns: Compiled graph application
    """
    workflow = build_graph()
    app = workflow.compile()
    
    print("\n" + "="*60)
    print("RCA GRAPH COMPILED SUCCESSFULLY!")
    print("="*60)
    
    return app


def run_rca_analysis(app, problem_description: str):
    """
    Run RCA analysis for a given problem - exact copy from notebook
    
    NOTE: This is the notebook's synchronous execution model.
    For production interactive use, see api.py for step-by-step execution.
    """
    print("\n" + "="*60)
    print("STARTING RCA ANALYSIS")
    print("="*60)
    print(f"\nProblem: {problem_description}\n")
    
    # Initialize state
    initial_state = {
        "problem": problem_description,
        "why_no": 0,
        "whys": [],
        "root_cause": "",
        "confidence_score": 0.0,
        "report": "",
        "user_input": "",
        "needs_validation": False,
        "retry_count": 0,
        "current_question": ""
    }
    
    # Run the graph
    final_state = app.invoke(initial_state)
    
    return final_state