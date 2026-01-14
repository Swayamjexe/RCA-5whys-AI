
# RCA 5-Whys Analysis AI Bot


## Overview

An AI-powered Root Cause Analysis (RCA) system that applies the **5 Whys methodology** to systematically identify underlying causes of problems.  
The project uses a graph-based execution flow with LLM-driven question generation, answer validation, early root-cause detection, and automated RCA report generation.

---
## Features

- Interactive 5 Whys questioning workflow
- Answer validation based on **specificity** and **relevance**
- Retry mechanism with improvement suggestions
- Early detection of **systematic root causes**
- Automated confidence scoring
- Standardized RCA report generation (Executive Summary, Analysis, Actions, Recommendations)
- CPU-only inference using GGUF models (no GPU required)
- Modular graph-based architecture

---


## Tech Stack

- Python
- LangGraph
- llama-cpp-python
- GGUF Quantized LLMs (Hugging Face)
- Gradio (UI)
- FastAPI (Backend)

---
## Architecture
## Installation



```bash
# Clone the repository
git clone <https://github.com/Swayamjexe/RCA-5whys-AI.git>
cd <RCA-5whys-AI>

# Create virtual environment (optional)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```
    
## Usage/Examples

```bash
#Run the application
python main.py
```


## Model Details

- **Generator Model**

    - Qwen2.5-3B-Instruct (Q4_K_M, GGUF)

    - Used for:

        - Why question generation

        - Root cause extraction

        - RCA report writing

- **Validator Model**

    - Qwen2.5-1.5B-Instruct (Q4_K_M, GGUF)

    - Used for:

        - Answer relevance scoring

        - Specificity scoring

        - Systematic root-cause detection
## Results

**Screenshots:**

**Demo:**
## Project Structure