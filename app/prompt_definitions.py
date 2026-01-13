"""
Prompt Definitions Module
Exact copy from notebook: PROMPT DEFINITIONS section
All prompts preserved verbatim with no modifications
"""


def create_why_prompt(problem: str, why_no: int, previous_whys: str) -> str:
    """Create prompt for asking why question - exact copy from notebook"""
    if why_no == 1:
        return f"""You are conducting a Root Cause Analysis using the 5 Whys technique.

Problem/Incident: {problem}

Generate the first "Why" question to dig deeper into this problem. The question should be direct and help understand the underlying cause.

Format your response as:
Why 1: [your question here]"""
    else:
        return f"""You are conducting a Root Cause Analysis using the 5 Whys technique.

Problem/Incident: {problem}

Previous questions and answers:
{previous_whys}

Generate the next "Why" question (Why {why_no}) based on the previous answer. Dig deeper into the root cause.

Format your response as:
Why {why_no}: [your question here]"""


def create_root_cause_prompt(problem: str, whys_context: str) -> str:
    """Create prompt for extracting root cause - exact copy from notebook"""
    return f"""You are analyzing a Root Cause Analysis session using the 5 Whys technique.

Problem/Incident: {problem}

5 Whys Analysis:
{whys_context}

Based on this analysis, extract and state the root cause in 1-2 clear sentences. Be specific and actionable.

Root Cause:"""


def create_validation_prompt(question: str, answer: str) -> str:
    """Create prompt for validating user answer - exact copy from notebook"""
    return f"""You are validating an answer in a Root Cause Analysis session.

Question: {question}
Answer: {answer}

Evaluate the answer on these criteria:
1. Specificity: Is the answer concrete and detailed, or vague and generic? (Rate 1-5, where 5 is very specific)
2. Relevance: Does the answer actually address the question asked? (Rate 1-5, where 5 is highly relevant)

Respond in this exact format:
Specificity: [score]
Relevance: [score]
Needs Improvement: [yes/no]
Suggestion: [If needs improvement, provide a brief suggestion for what additional details would help]"""


def create_report_prompt(problem: str, whys_context: str, root_cause: str, confidence: float, section: str) -> str:
    """Create prompt for generating specific report section - exact copy from notebook"""
    
    base_context = f"""Problem/Incident: {problem}

Analysis Process:
{whys_context}

Root Cause: {root_cause}
Confidence Level: {confidence:.1f}%"""
    
    if section == "executive":
        return f"""{base_context}

Write the EXECUTIVE SUMMARY section for this RCA report. Include:
- Brief incident overview (2-3 sentences)
- High-level root cause statement
- Overall impact

Keep it concise and executive-focused."""
    
    elif section == "analysis":
        return f"""{base_context}

Write the DETAILED ANALYSIS section. Include:
- Problem Statement with impact details
- The 5 Whys methodology application
- Step-by-step breakdown of each Why and answer
- Root cause identification with confidence reasoning

Be thorough and technical."""
    
    elif section == "actions":
        return f"""{base_context}

Write the CORRECTIVE AND PREVENTIVE ACTIONS section. Include:
- Immediate corrective actions (3 specific items)
- Long-term preventive measures (3 specific items)
- Each action should be concrete and actionable

Focus on practical solutions."""
    
    elif section == "recommendations":
        return f"""{base_context}

Write the RECOMMENDATIONS AND FOLLOW-UP section. Include:
- Process improvement recommendations (2-3 items)
- Monitoring and alerting improvements
- Follow-up actions and review schedule
- Key learnings

Make it actionable and forward-looking."""
    
    return ""