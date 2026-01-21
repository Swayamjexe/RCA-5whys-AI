"""
Model Loading Module - SPLIT ARCHITECTURE
Text Models: Qwen 2.5 3B (Generator) + 1.5B (Validator)
Vision Model: Qwen2.5-VL-3B (Only for image analysis)
"""

from llama_cpp import Llama
from llama_cpp.llama_chat_format import Qwen25VLChatHandler
import base64
from io import BytesIO
from PIL import Image
import os

# Global variables for text models
gen_model = None
val_model = None

# Global variables for vision model
vision_model = None
vision_chat_handler = None

def load_model():
    """
    Load all models optimized for CPU:
    - Text Generator (Qwen 2.5 3B)
    - Text Validator (Qwen 2.5 1.5B)
    - Vision Analyzer (Qwen2.5-VL-3B) - loaded on demand
    """
    global gen_model, val_model
    
    print("\n" + "="*50)
    print("LOADING TEXT MODELS (CPU OPTIMIZED)")
    print("="*50)

    # 1. Load Generator Model (Qwen 2.5 3B)
    print("\n[1/2] Loading Text Generator (Qwen 2.5 3B)...")
    gen_model = Llama.from_pretrained(
        repo_id="bartowski/Qwen2.5-3B-Instruct-GGUF",
        filename="Qwen2.5-3B-Instruct-Q4_K_M.gguf",
        verbose=False,
        n_ctx=4096,
        n_threads=4,
        n_batch=512
    )

    # 2. Load Validator Model (Qwen 2.5 1.5B)
    print("[2/2] Loading Text Validator (Qwen 2.5 1.5B)...")
    val_model = Llama.from_pretrained(
        repo_id="bartowski/Qwen2.5-1.5B-Instruct-GGUF",
        filename="Qwen2.5-1.5B-Instruct-Q4_K_M.gguf",
        verbose=False,
        n_ctx=1024,
        n_threads=2,
        n_batch=512
    )
    
    print("\n✅ Text models loaded successfully!")
    print("📝 Vision model will be loaded when first image is uploaded")

def load_vision_model():
    """
    Load vision model on-demand (only when first image is uploaded)
    """
    global vision_model, vision_chat_handler
    
    if vision_model is not None:
        print("Vision model already loaded, skipping...")
        return
    
    print("\n" + "="*50)
    print("LOADING VISION MODEL (FIRST IMAGE UPLOAD)")
    print("="*50)
    
    print("\n[Vision] Initializing Qwen2.5-VL-3B...")
    
    # Initialize chat handler for vision processing
    vision_chat_handler = Qwen25VLChatHandler.from_pretrained(
        repo_id="unsloth/Qwen2.5-VL-3B-Instruct-GGUF",
        filename="*mmproj-F16.gguf*",
    )
    
    # Load the vision model
    vision_model = Llama.from_pretrained(
        repo_id="unsloth/Qwen2.5-VL-3B-Instruct-GGUF",
        filename="Qwen2.5-VL-3B-Instruct-Q4_K_M.gguf",
        chat_handler=vision_chat_handler,
        verbose=False,
        n_ctx=4096,
        n_threads=4,
        n_batch=512,
        logits_all=True
    )
    
    print("✅ Vision model loaded successfully!")

def encode_image_to_base64(image_path: str) -> str:
    """
    Convert image file to base64 string for model input
    """
    with Image.open(image_path) as img:
        # Resize if too large to save memory
        max_size = (1024, 1024)
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        buffered = BytesIO()
        img.save(buffered, format=img.format or "PNG")
        img_bytes = buffered.getvalue()
        
    return base64.b64encode(img_bytes).decode('utf-8')

def generate_response(prompt: str) -> str:
    """
    Generate response using the main TEXT GENERATOR model (3B)
    """
    response = gen_model.create_chat_completion(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300,
        temperature=0.7
    )
    return response["choices"][0]["message"]["content"].strip()

def generate_validation_response(prompt: str) -> str:
    """
    Generate response using the TEXT VALIDATOR model (1.5B)
    """
    response = val_model.create_chat_completion(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200,
        temperature=0.1
    )
    return response["choices"][0]["message"]["content"].strip()

def generate_response_extended(prompt: str, max_tokens: int = 300) -> str:
    """
    Generate response using TEXT GENERATOR model with custom token limit
    """
    response = gen_model.create_chat_completion(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=0.7
    )
    return response["choices"][0]["message"]["content"].strip()

def analyze_image(image_path: str, analysis_prompt: str) -> str:
    """
    Analyze image using VISION MODEL
    Loads vision model on first call
    """
    if not os.path.exists(image_path):
        return "Error: Image file not found"
    
    # Load vision model if not already loaded
    if vision_model is None:
        load_vision_model()
    
    print(f"\n🖼️  Analyzing image: {image_path}")
    
    # Encode image to base64
    image_b64 = encode_image_to_base64(image_path)
    
    # Create multimodal message
    messages = [{
        "role": "user",
        "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
            {"type": "text", "text": analysis_prompt}
        ]
    }]
    
    response = vision_model.create_chat_completion(
        messages=messages,
        max_tokens=300,
        temperature=0.7
    )
    
    analysis = response["choices"][0]["message"]["content"].strip()
    print(f"✅ Image analyzed successfully")
    
    return analysis

# Only run if executed directly
if __name__ == "__main__":
    load_model()
    print("\n✅ Text models ready!")
    print("Vision model will load on first image upload")