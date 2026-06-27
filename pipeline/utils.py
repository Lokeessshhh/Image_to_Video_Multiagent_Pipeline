import os
import json
import base64
import io
from typing import List, Dict, Any, Type
from pydantic import BaseModel
import requests
from PIL import Image
from groq import Groq

def call_nvidia_chat(
    model: str,
    messages: List[Dict[str, Any]],
    json_mode: bool = False,
    temperature: float = 0.1
) -> str:
    """Wrapper around Nvidia NIM Chat Completion API."""
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        raise ValueError("NVIDIA_API_KEY not found in environment variables. Please check your .env file.")
        
    import time
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
        
    retries = 3
    for attempt in range(retries):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            if response.status_code != 200:
                raise Exception(f"Nvidia NIM API Error {response.status_code}: {response.text}")
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            if attempt == retries - 1:
                raise e
            wait_time = 2 ** attempt
            print(f" -> Nvidia API call failed (attempt {attempt+1}/{retries}): {e}. Retrying in {wait_time}s...")
            time.sleep(wait_time)


def get_groq_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in environment variables. Please check your .env file.")
    return Groq(api_key=api_key)

def encode_image_to_base64(image_path: str) -> str:
    """Read an image file, resize it to a max dimension of 1024px, and encode it as a base64 string."""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found at: {image_path}")
    
    try:
        with Image.open(image_path) as img:
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            # Resize if dimension exceeds 1024
            max_dim = 1024
            width, height = img.size
            if max(width, height) > max_dim:
                if width > height:
                    new_width = max_dim
                    new_height = int(height * (max_dim / width))
                else:
                    new_height = max_dim
                    new_width = int(width * (max_dim / height))
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=80)
            return base64.b64encode(buffer.getvalue()).decode("utf-8")
    except Exception as e:
        print(f"PIL compression failed for {image_path}: {e}. Falling back to uncompressed base64.")
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

def get_image_mime_type(image_path: str) -> str:
    ext = os.path.splitext(image_path)[1].lower()
    if ext in [".jpg", ".jpeg"]:
        return "image/jpeg"
    elif ext == ".png":
        return "image/png"
    elif ext == ".webp":
        return "image/webp"
    return "image/jpeg"  # Default fallback

def call_groq_chat(
    model: str, 
    messages: List[Dict[str, Any]], 
    json_mode: bool = False,
    temperature: float = 0.1
) -> str:
    """Wrapper around Groq Chat Completion API."""
    import time
    client = get_groq_client()
    
    extra_params = {}
    if json_mode:
        extra_params["response_format"] = {"type": "json_object"}
        
    retries = 3
    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=4096,
                **extra_params
            )
            return response.choices[0].message.content
        except Exception as e:
            err_msg = str(e)
            is_rate_limit = "rate_limit" in err_msg or "429" in err_msg or "RateLimit" in type(e).__name__
            if is_rate_limit and model not in ("llama-3.3-70b-versatile", "llama-3.1-8b-instant"):
                fallback = "llama-3.3-70b-versatile" if ("120b" in model or "27b" in model) else "llama-3.1-8b-instant"
                print(f" -> Model '{model}' rate limited. Falling back to '{fallback}'...")
                model = fallback
            if attempt == retries - 1:
                raise e
            wait_time = 2 ** attempt
            print(f" -> Groq API call failed (attempt {attempt+1}/{retries}): {e}. Retrying in {wait_time}s...")
            time.sleep(wait_time)

def call_groq_structured(
    model: str,
    system_prompt: str,
    user_prompt: str,
    response_model: Type[BaseModel],
    temperature: float = 0.1
) -> Any:
    """
    Simulate structured output using Groq's JSON mode.
    Forces the model to conform to the Pydantic schema by appending schema definition.
    """
    schema_json = json.dumps(response_model.model_json_schema(), indent=2)
    
    system_message = (
        f"{system_prompt}\n\n"
        f"You MUST return your output in JSON format conforming strictly to the following JSON schema:\n"
        f"{schema_json}\n\n"
        f"Do not include any chat prefix, suffix, explanation, or markdown backticks outside of the JSON object."
    )
    
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_prompt}
    ]
    
    raw_content = call_groq_chat(model, messages, json_mode=True, temperature=temperature)
    try:
        data = json.loads(raw_content)
        return response_model.model_validate(data)
    except Exception as e:
        # Simple self-repair retry
        print(f"JSON parsing error: {e}. Retrying with strict instruction...")
        repair_messages = messages + [
            {"role": "assistant", "content": raw_content},
            {"role": "user", "content": f"The response was not valid JSON matching the schema. Error: {e}. Re-output the correct JSON object now."}
        ]
        raw_repair = call_groq_chat(model, repair_messages, json_mode=True, temperature=temperature)
        data = json.loads(raw_repair)
        return response_model.model_validate(data)

def extract_json_from_text(text: str) -> str:
    """Extracts a JSON object or array from a text response that may contain thinking blocks or other text."""
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1:
        return text[start:end+1]
    
    # Try finding an array if object is not found
    start_arr = text.find('[')
    end_arr = text.rfind(']')
    if start_arr != -1 and end_arr != -1:
        return text[start_arr:end_arr+1]
        
    return text.strip()
