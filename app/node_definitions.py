"""
Node Definitions Module
Exact copy from notebook: NODE DEFINITIONS section
All node logic, inputs, outputs, and side effects preserved as-is

NOTE: Interactive input() calls are replaced with callback mechanism
for production use (API/UI will provide answers via state)
"""

from app.helpers import RCAState, format_whys_context, calculate_answer_quality_score, export_report_to_markdown
from app.prompt_definitions import (
    create_why_prompt,
    create_root_cause_prompt,
    create_validation_prompt,
    create_report_prompt
)
from app.model_loading import generate_response, generate_response_extended, generate_validation_response


def why_asker(state: RCAState) -> RCAState:
    """Node that generates why questions - exact copy from notebook"""
    print(f"\n{'='*60}")
    print(f"WHY ASKER NODE - Iteration {state['why_no'] + 1}")
    print(f"{'='*60}")
    
    # Increment why number
    state["why_no"] += 1
    
    # Generate why question
    previous_whys = format_whys_context(state["whys"])
    prompt = create_why_prompt(state["problem"], state["why_no"], previous_whys)
    why_question = generate_response(prompt)
    
    # Extract just the question part
    if ":" in why_question:
        why_question = why_question.split(":", 1)[1].strip()
    
    print(f"\nGenerated Question: {why_question}")
    
    # Store current question for validation
    state["current_question"] = why_question
    
    # In production: user_input comes from API/UI, not input()
    # The notebook logic expected input() here, but we'll receive it via state
    # Set flag to indicate we need user input
    state["needs_validation"] = True
    state["retry_count"] = 0
    
    return state


def answer_validator(state: RCAState) -> RCAState:
    """Node that validates user answers for quality - exact copy from notebook"""
    print(f"\n{'='*60}")
    print("ANSWER VALIDATOR NODE")
    print(f"{'='*60}")
    
    question = state.get("current_question", "")
    answer = state.get("user_input", "")
    
    # Generate validation
    validation_prompt = create_validation_prompt(question, answer)
    validation_response = generate_validation_response(validation_prompt)
    
    print(f"\nValidating answer...")
    
    # Parse validation response
    specificity = 3.0  # Default
    relevance = 3.0    # Default
    needs_improvement = False
    
    for line in validation_response.split('\n'):
        if 'Specificity:' in line:
            try:
                specificity = float(line.split(':')[1].strip().split()[0])
            except:
                pass
        elif 'Relevance:' in line:
            try:
                relevance = float(line.split(':')[1].strip().split()[0])
            except:
                pass
        elif 'Needs Improvement:' in line:
            needs_improvement = 'yes' in line.lower()
    
    # Calculate quality score
    quality_score = (specificity + relevance) / 2
    
    print(f"Specificity: {specificity}/5")
    print(f"Relevance: {relevance}/5")
    print(f"Quality Score: {quality_score:.1f}/5")
    
    # Check if answer needs improvement
    if needs_improvement and quality_score < 3.0 and state.get("retry_count", 0) < 1:
        print(f"\n⚠️  Answer could be more specific or relevant.")
        suggestion = validation_response.split('Suggestion:')[-1].strip() if 'Suggestion:' in validation_response else "Please provide more details."
        print(f"Suggestion: {suggestion}")
        
        # In production: improved_answer comes from API/UI via state
        # Set flag to request improvement
        state["needs_improvement"] = True
        state["improvement_suggestion"] = suggestion
        state["retry_count"] = state.get("retry_count", 0) + 1
        
        # Check if improved_input is already provided
        if not state.get("improved_input"):
            return state
        else:
            # Use improved input
            state["user_input"] = state["improved_input"]
            state["improved_input"] = ""
            # Re-validate
            return answer_validator(state)
    
    # Accept the answer
    state["whys"].append({
        "question": question,
        "answer": state["user_input"],
        "quality_score": quality_score
    })
    
    state["needs_validation"] = False
    state["needs_improvement"] = False
    print(f"✓ Answer accepted")
    
    return state


def root_cause_extractor(state: RCAState) -> RCAState:
    """Node that extracts root cause - exact copy from notebook"""
    print(f"\n{'='*60}")
    print("ROOT CAUSE EXTRACTOR NODE")
    print(f"{'='*60}")
    
    whys_context = format_whys_context(state["whys"])
    prompt = create_root_cause_prompt(state["problem"], whys_context)
    
    root_cause = generate_response(prompt)
    state["root_cause"] = root_cause

    # Calculate confidence score
    answer_quality = calculate_answer_quality_score(state["whys"])
    
    # Factors for confidence:
    # 1. Answer quality (0-100)
    # 2. Completeness (did we do all 5 whys?) - 20 points
    # 3. Logical flow bonus - 10 points

    completeness_score = 20 if len(state["whys"]) == 5 else (len(state["whys"]) / 5 * 20)
    logical_flow_bonus = 10  # Simplified for MVP

    confidence = (answer_quality * 0.7) + completeness_score + logical_flow_bonus
    confidence = min(100, max(0, confidence))  # Clamp between 0-100
    
    state["confidence_score"] = confidence
    
    print(f"\nExtracted Root Cause: {root_cause}")
    print(f"\n📊 Confidence Score: {confidence:.1f}%")
    print(f"   - Answer Quality: {answer_quality:.1f}%")
    print(f"   - Completeness: {completeness_score:.1f}/20")
    print(f"   - Logical Flow: {logical_flow_bonus}/10")
    
    return state


def report_generator(state: RCAState) -> RCAState:
    """Node that generates final standardized RCA report - exact copy from notebook"""
    print(f"\n{'='*60}")
    print("REPORT GENERATOR NODE")
    print(f"{'='*60}")
    print("\nGenerating comprehensive report in sections...")
    
    whys_context = format_whys_context(state["whys"])
    
    # Section-based generation to overcome token limits
    sections = {}
    
    print("\n[1/4] Generating Executive Summary...")
    sections["executive"] = generate_response_extended(
        create_report_prompt(
            state["problem"],
            whys_context,
            state["root_cause"],
            state["confidence_score"],
            "executive"
        ),
        max_tokens=400
    )
    
    print("[2/4] Generating Detailed Analysis...")
    sections["analysis"] = generate_response_extended(
        create_report_prompt(
            state["problem"],
            whys_context,
            state["root_cause"],
            state["confidence_score"],
            "analysis"
        ),
        max_tokens=500
    )
    
    print("[3/4] Generating Corrective Actions...")
    sections["actions"] = generate_response_extended(
        create_report_prompt(
            state["problem"],
            whys_context,
            state["root_cause"],
            state["confidence_score"],
            "actions"
        ),
        max_tokens=400
    )
    
    print("[4/4] Generating Recommendations...")
    sections["recommendations"] = generate_response_extended(
        create_report_prompt(
            state["problem"],
            whys_context,
            state["root_cause"],
            state["confidence_score"],
            "recommendations"
        ),
        max_tokens=400
    )
    
    # Assemble complete report
    complete_report = f"""## 1. EXECUTIVE SUMMARY

{sections["executive"]}

---

## 2. DETAILED ANALYSIS

{sections["analysis"]}

---

## 3. CORRECTIVE AND PREVENTIVE ACTIONS

{sections["actions"]}

---

## 4. RECOMMENDATIONS AND FOLLOW-UP

{sections["recommendations"]}

---
"""
    
    state["report"] = complete_report
    
    print("\n" + "="*60)
    print("STANDARDIZED RCA REPORT")
    print("="*60)
    print(complete_report)
    print("\n" + "="*60)
    print(f"Overall Confidence: {state['confidence_score']:.1f}%")
    print("="*60)
    
    # Export to markdown
    filename = export_report_to_markdown(state)
    print(f"\n💾 Report exported to: {filename}")
    
    return state