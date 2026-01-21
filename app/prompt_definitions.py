"""
Prompt Definitions Module - MULTIMODAL VERSION
Added prompts for image analysis
"""


def create_why_prompt(problem: str, why_no: int, previous_whys: str) -> str:
    """Create prompt for asking why question (unchanged)"""
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


def create_image_analysis_prompt(question: str, text_answer: str = "") -> str:
    """
    NEW: Prompt for analyzing uploaded images
    Extracts key evidence and technical details from the image
    """
    if text_answer:
        return f"""You are analyzing an image provided as evidence for a Root Cause Analysis question.

Question: {question}
User's Text Answer: {text_answer}

Analyze the image and provide:
1. Key technical details visible in the image (equipment, error messages, conditions)
2. Any anomalies, failures, or important observations
3. How the visual evidence relates to the question

Keep your analysis factual, concise, and focused on details that help identify the root cause.
Format: Bullet points or short paragraphs.

Image Analysis:"""
    else:
        return f"""You are analyzing an image provided as evidence for a Root Cause Analysis question.

Question: {question}

Analyze the image and describe:
1. What you see (equipment, screens, conditions, errors)
2. Any visible problems, anomalies, or failure indicators
3. Technical details that could help identify root causes

Be specific and factual. Focus on observable details.

Image Analysis:"""


def create_root_cause_prompt(problem: str, whys_context: str) -> str:
    """Create prompt for extracting root cause (unchanged)"""
    return f"""You are analyzing a Root Cause Analysis session using the 5 Whys technique.

Problem/Incident: {problem}

5 Whys Analysis:
{whys_context}

Based on this analysis, extract and state the root cause in 1-2 clear sentences. Be specific and actionable.

Root Cause:"""


def create_validation_prompt(question: str, answer: str, has_image: bool = False) -> str:
    """
    Create prompt for validating user answer
    UPDATED: Can request image evidence if answer is vague
    """
    image_note = ""
    if has_image:
        image_note = "\n\nNote: The user has provided an image as supporting evidence."
    
    return f"""You are validating an answer in a Root Cause Analysis session.

Question: {question}
Answer: {answer}{image_note}

Evaluate the answer on these criteria:
1. Specificity: Is the answer concrete and detailed, or vague and generic? (Rate 1-5, where 5 is very specific)
2. Relevance: Does the answer actually address the question asked? (Rate 1-5, where 5 is highly relevant)

Respond in this exact format:
Specificity: [score]
Relevance: [score]
Needs Improvement: [yes/no]
Request Image: [yes/no - only if answer is too vague and visual evidence would help]
Suggestion: [If needs improvement, provide a brief suggestion. If requesting image, explain what kind of visual evidence would help]"""


def create_systematic_root_cause_check_prompt(answer: str) -> str:
    """Check if answer indicates systematic root cause (unchanged)"""
    return f"""You are evaluating whether the given answer identifies a SYSTEMATIC root cause.

Definition: A SYSTEMATIC root cause refers to failures at the organizational, process, or system level – not individual mistakes.

An answer IS systematic if it indicates any of the following:
- Missing, skipped, inadequate, or undefined PROCESS
- Missing, weak, unenforced, or unclear POLICY
- Lack of TRAINING or standardized knowledge
- Skipped, absent, or poorly managed PREVENTIVE MAINTENANCE
- Design or failure of a SYSTEM, workflow, or tool
- Organizational or structural failure
- Repeated or routine issues (even if performed by people)

An answer IS NOT systematic if it ONLY refers to:
- A single individual's mistake or negligence
- A one-time human error with no process implication
- Random equipment failure with no maintenance or system implication

⚠️ Important Rule:
If the answer mentions that something was "skipped," "not done," "not followed," or "missing" and that thing is normally governed by a process, policy, or schedule, it MUST be classified as SYSTEMATIC.

Input Answer:
"{answer}"

Output Rules:
Respond with ONLY ONE of the following (no explanation):
Systematic: yes
OR
Systematic: no"""


def create_full_report_prompt(problem, whys, root_cause, confidence):
    """Create prompt for generating complete report (unchanged)"""
    return f"""
Problem/Incident:
{problem}

Analysis Process:
{whys}

Root Cause:
{root_cause}

Confidence Level:
{confidence:.1f}%

INSTRUCTIONS:
- Produce a COMPLETE RCA report
- Use concise, professional language
- Never leave a section incomplete
- Prefer brevity over truncation

STRUCTURE:

## 1. Executive Summary
(2–4 paragraphs)

## 2. Detailed Analysis
- Problem statement
- 5 Whys breakdown
- Root cause explanation

## 3. Corrective and Preventive Actions
- Immediate (3 bullets)
- Long-term (3 bullets)

## 4. Recommendations and Follow-up
- Process improvements
- Monitoring
- Review schedule
"""