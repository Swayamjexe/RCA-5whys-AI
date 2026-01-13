"""
Model Loading Module
Optimized for i5-8th Gen CPU using llama-cpp-python
Loads two separate models:
1. Generator: Qwen 2.5 3B (for asking questions and reporting)
2. Validator: Qwen 2.5 1.5B (for judging answers)
"""

from llama_cpp import Llama
import os

# Global variables to store model components
gen_model = None
val_model = None

def load_model():
    """
    Load GGUF models optimized for CPU
    """
    global gen_model, val_model
    
    print("\n" + "="*50)
    print("LOADING LOCAL GGUF MODELS (CPU OPTIMIZED)")
    print("="*50)

    # 1. Load Generator Model (Qwen 2.5 3B)
    print("\n[1/2] Loading Generator (Qwen 2.5 3B)...")
    gen_model = Llama.from_pretrained(
        repo_id="bartowski/Qwen2.5-3B-Instruct-GGUF",
        filename="Qwen2.5-3B-Instruct-Q4_K_M.gguf",
        verbose=False,
        n_ctx=4096,      # Context for 5-Whys history
        n_threads=4,     # Use 4 physical cores
        n_batch=512
    )

    # 2. Load Validator Model (Qwen 2.5 1.5B)
    print("[2/2] Loading Validator (Qwen 2.5 1.5B)...")
    val_model = Llama.from_pretrained(
        repo_id="bartowski/Qwen2.5-1.5B-Instruct-GGUF",
        filename="Qwen2.5-1.5B-Instruct-Q4_K_M.gguf",
        verbose=False,
        n_ctx=1024,      # Short context for validation
        n_threads=2,     # Lightweight background thread
        n_batch=512
    )
    
    print("\n✅ Both models loaded successfully on CPU!")

def generate_response(prompt: str) -> str:
    """
    Generate response using the main GENERATOR model (3B)
    USES CHAT COMPLETION to prevent hallucinations
    """
    # We wrap the prompt in a user message. 
    # The model handles strict stop tokens (<|im_end|>) automatically in this mode.
    response = gen_model.create_chat_completion(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300,
        temperature=0.7
    )
    return response["choices"][0]["message"]["content"].strip()

def generate_validation_response(prompt: str) -> str:
    """
    Generate response using the VALIDATOR model (1.5B)
    """
    response = val_model.create_chat_completion(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200,   
        temperature=0.1   # Lower temp for strict judging
    )
    return response["choices"][0]["message"]["content"].strip()

def generate_response_extended(prompt: str, max_tokens: int = 300) -> str:
    """
    Generate response using GENERATOR model with custom token limit
    """
    response = gen_model.create_chat_completion(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=0.7
    )
    return response["choices"][0]["message"]["content"].strip()

# Only run if executed directly
if __name__ == "__main__":
    load_model()





















# """
# Model Loading Module
# Exact copy from notebook: MODEL LOADING section
# All parameters, device settings, and configurations preserved as-is
# """

# from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
# import torch

# # Global variables to store model components (initialized once)
# model = None
# tokenizer = None
# llm_pipeline = None


# def load_model():
#     """
#     Load model exactly as defined in notebook
#     Returns: None (sets global variables)
#     """
#     global model, tokenizer, llm_pipeline
    
#     print("Loading model...")
#     model_name = "Qwen/Qwen2.5-3B-Instruct"
    
#     print("Loading tokenizer...")
#     tokenizer = AutoTokenizer.from_pretrained(
#         model_name, 
#         trust_remote_code=True
#     )
    
#     print("Loading model weights...")
#     model = AutoModelForCausalLM.from_pretrained(
#         model_name,
#         torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
#         device_map="auto",
#         trust_remote_code=True
#     )
    
#     print("Creating pipeline...")
#     # Create pipeline
#     llm_pipeline = pipeline(
#         "text-generation",
#         model=model,
#         tokenizer=tokenizer,
#         max_new_tokens=300,
#         temperature=0.7,
#         do_sample=True
#     )
    
#     print("Model loaded successfully!")


# def generate_response(prompt: str) -> str:
#     """Generate response from LLM - exact copy from notebook"""
#     messages = [{"role": "user", "content": prompt}]
#     result = llm_pipeline(messages)
#     return result[0]["generated_text"][-1]["content"].strip()


# def generate_response_extended(prompt: str, max_tokens: int = 300) -> str:
#     """Generate response with configurable token limit - exact copy from notebook"""
#     messages = [{"role": "user", "content": prompt}]
#     pipe = pipeline(
#         "text-generation",
#         model=model,
#         tokenizer=tokenizer,
#         max_new_tokens=max_tokens,
#         temperature=0.7,
#         do_sample=True
#     )
#     result = pipe(messages)
#     return result[0]["generated_text"][-1]["content"].strip()


# def get_model_components():
#     """Return model components for external use"""
#     return model, tokenizer, llm_pipeline


# # Only run if executed directly (for pre-downloading)
# if __name__ == "__main__":
#     load_model()
#     print("\n✅ Model download and initialization complete!")
#     print("You can now run: python main.py")