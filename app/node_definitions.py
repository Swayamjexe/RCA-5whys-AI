"""
Node Definitions Module - MULTIMODAL VERSION (SPLIT ARCHITECTURE)
Text models for reasoning, Vision model only for image analysis
"""

from app.helpers import RCAState, format_whys_context, calculate_answer_quality_score, export_report_to_markdown
from app.prompt_definitions import (
    create_why_prompt,
    create_root_cause_prompt,
    create_validation_prompt,
    create_full_report_prompt,
    create_systematic_root_cause_check_prompt,
    create_image_analysis_prompt
)
from app.model_loading import (
    generate_response,
    generate_response_extended,
    generate_validation_response,
    analyze_image
)


def why_asker(state: RCAState) -> RCAState:
    """Node that generates why questions - TEXT ONLY"""
    print(f"\n{'='*60}")
    print(f"WHY ASKER NODE - Iteration {state['why_no'] + 1}")
    print(f"{'='*60}")
    
    state["why_no"] += 1
    
    previous_whys = format_whys_context(state["whys"])
    prompt = create_why_prompt(state["problem"], state["why_no"], previous_whys)
    
    # Generate question using TEXT model
    why_question = generate_response(prompt)
    
    # Remove duplicate "Why X:" prefix if present
    if ":" in why_question:
        parts = why_question.split(":", 1)
        if parts[0].strip().lower().startswith("why"):
            why_question = parts[1].strip()
    
    print(f"\nGenerated Question: {why_question}")
    
    state["current_question"] = why_question
    state["needs_validation"] = True
    state["retry_count"] = 0
    state["image_requested"] = False  # Reset image request flag
    
    return state


def answer_validator(state: RCAState) -> RCAState:
    """
    Node that validates user answers - MULTIMODAL VERSION
    Uses TEXT model for validation, VISION model only for image analysis
    """
    print(f"\n{'='*60}")
    print("ANSWER VALIDATOR NODE")
    print(f"{'='*60}")
    
    question = state.get("current_question", "")
    answer = state.get("improved_input", "") or state.get("user_input", "")
    current_image = state.get("current_image")
    
    # Step 1: Analyze image if provided (VISION MODEL)
    image_description = None
    if current_image:
        print(f"\n🖼️  Image provided: {current_image}")
        print("Analyzing image with vision model...")
        
        image_analysis_prompt = create_image_analysis_prompt(question, answer)
        image_description = analyze_image(current_image, image_analysis_prompt)
        
        print(f"Image Analysis: {image_description[:150]}...")
        
        # Append image description to the answer for validation
        augmented_answer = f"{answer}\n\n[Uploaded Image Description: {image_description}]"
    else:
        augmented_answer = answer
    
    # Step 2: Validate answer using TEXT VALIDATOR model
    validation_prompt = create_validation_prompt(question, augmented_answer, has_image=(current_image is not None))
    validation_response = generate_validation_response(validation_prompt)
    
    print(f"\nValidating answer...")
    
    # Parse validation response
    specificity = 3.0
    relevance = 3.0
    needs_improvement = False
    image_requested = False
    
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
        elif 'Request Image:' in line:
            image_requested = 'yes' in line.lower()
    
    quality_score = (specificity + relevance) / 2
    
    # Bonus for image-backed answers
    if current_image:
        quality_score = min(5.0, quality_score + 0.3)
        print(f"✅ Image evidence bonus applied (+0.3)")
    
    print(f"Specificity: {specificity}/5")
    print(f"Relevance: {relevance}/5")
    print(f"Quality Score: {quality_score:.1f}/5")
    
    # Check if answer needs improvement
    if needs_improvement and quality_score < 3.0 and state.get("retry_count", 0) < 1:
        print(f"\n⚠️  Answer could be more specific or relevant.")
        suggestion = validation_response.split('Suggestion:')[-1].strip() if 'Suggestion:' in validation_response else "Please provide more details."
        
        # Check if image is requested
        if image_requested and not current_image:
            suggestion = f"📷 Image evidence requested: {suggestion}"
            print(f"📷 System requesting image evidence")
        
        print(f"Suggestion: {suggestion}")
        
        state["needs_improvement"] = True
        state["improvement_suggestion"] = suggestion
        state["image_requested"] = image_requested
        state["retry_count"] = state.get("retry_count", 0) + 1
        
        if not state.get("improved_input"):
            return state
        else:
            state["user_input"] = state["improved_input"]
            state["improved_input"] = ""
            return answer_validator(state)
    
    final_answer = state.get("improved_input", "") or state.get("user_input", "")
    
    # Store answer with image metadata
    state["whys"].append({
        "question": question,
        "answer": final_answer,
        "quality_score": quality_score,
        "has_image": current_image is not None,
        "image_path": current_image if current_image else None,
        "image_analysis": image_description if current_image else None
    })
    
    state["needs_validation"] = False
    state["needs_improvement"] = False
    state["improved_input"] = ""
    state["image_requested"] = False
    
    print(f"✓ Answer accepted")
    
    # Early stopping check (Why 4+)
    if state["why_no"] >= 4:
        print(f"\n[Early Stop Check] Evaluating if systematic root cause reached...")
        
        systematic_check_prompt = create_systematic_root_cause_check_prompt(final_answer)
        systematic_response = generate_validation_response(systematic_check_prompt)
        
        is_systematic = False
        for line in systematic_response.split('\n'):
            if 'Systematic:' in line:
                is_systematic = 'yes' in line.lower()
                break
        
        if is_systematic:
            print(f"✓ SYSTEMATIC ROOT CAUSE DETECTED at Why {state['why_no']}!")
            state["early_root_cause_found"] = True
        else:
            print(f"  → Not yet systematic, continuing...")
            state["early_root_cause_found"] = False
    else:
        state["early_root_cause_found"] = False
    
    return state


def root_cause_extractor(state: RCAState) -> RCAState:
    """Node that extracts root cause - TEXT ONLY"""
    print(f"\n{'='*60}")
    print("ROOT CAUSE EXTRACTOR NODE")
    print(f"{'='*60}")
    
    whys_context = format_whys_context(state["whys"])
    prompt = create_root_cause_prompt(state["problem"], whys_context)
    
    # Extract root cause using TEXT model
    root_cause = generate_response(prompt)
    state["root_cause"] = root_cause

    # Calculate confidence score
    answer_quality = calculate_answer_quality_score(state["whys"])
    
    completeness_score = 20 if len(state["whys"]) == 5 else (len(state["whys"]) / 5 * 20)
    logical_flow_bonus = 10
    
    # Extra confidence for image evidence
    has_images = any(why.get('has_image') for why in state["whys"])
    image_bonus = 5 if has_images else 0

    confidence = (answer_quality * 0.7) + completeness_score + logical_flow_bonus + image_bonus
    confidence = min(100, max(0, confidence))
    
    state["confidence_score"] = confidence
    
    print(f"\nExtracted Root Cause: {root_cause}")
    print(f"\n📊 Confidence Score: {confidence:.1f}%")
    print(f"   - Answer Quality: {answer_quality:.1f}%")
    print(f"   - Completeness: {completeness_score:.1f}/20")
    print(f"   - Logical Flow: {logical_flow_bonus}/10")
    if image_bonus:
        print(f"   - Visual Evidence: +{image_bonus}")
    
    return state


def report_generator(state: RCAState) -> RCAState:
    """Node that generates final report - TEXT ONLY"""
    print(f"\n{'='*60}")
    print("REPORT GENERATOR NODE")
    print(f"{'='*60}")
    print("\nGenerating full RCA report...")

    prompt = create_full_report_prompt(
        state["problem"],
        format_whys_context(state["whys"]),
        state["root_cause"],
        state["confidence_score"]
    )

    # Generate report using TEXT model
    report = generate_response_extended(prompt, max_tokens=1400)

    state["report"] = report
    export_report_to_markdown(state)
    
    print("\n✅ Report generated and exported!")
    
    return state