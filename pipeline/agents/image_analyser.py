import os
import json
from typing import List
from pydantic import BaseModel, Field
from pipeline.state import PipelineState, ImageAnalysis
from pipeline.utils import get_image_mime_type, encode_image_to_base64, call_groq_chat, extract_json_from_text, call_nvidia_chat

class ImageAnalysisBatch(BaseModel):
    analyses: List[ImageAnalysis] = Field(description="List of image analyses, corresponding in order to the images provided")

def analyze_images(state: PipelineState) -> PipelineState:
    """
    Uses the vision model qwen/qwen3.6-27b to analyze all images in batches of up to 5.
    Extracts descriptive detail, color palettes, lighting, and mood.
    """
    print(f"\n--- [2/5] Running Image Analyser ---")
    image_paths = state.get("image_paths", [])
    if not image_paths:
        print("No images found in state to analyze!")
        state["image_analyses"] = []
        return state

    print(f"Total images to analyze: {len(image_paths)}")
    analyses: List[ImageAnalysis] = []
    
    model = "meta/llama-4-maverick-17b-128e-instruct"
    batch_size = 5
    print(f"Routing to NVIDIA NIM Model: '{model}' with batch size {batch_size}")

    for i in range(0, len(image_paths), batch_size):
        batch_paths = image_paths[i:i+batch_size]
        print(f"Analyzing batch {i//batch_size + 1} ({len(batch_paths)} images)...")
        
        # Prepare content list for the multimodal API call
        filenames = [os.path.basename(p) for p in batch_paths]
        prompt_text = (
            f"You are a computer vision assistant. You are given a batch of {len(batch_paths)} images in order.\n"
            f"Please analyze each image and return a JSON list of analyses conforming to the ImageAnalysisBatch schema.\n"
            f"Here are the filenames of the images in the exact order they are attached:\n"
            + "\n".join([f"{idx+1}. {fname}" for idx, fname in enumerate(filenames)])
            + "\n\nFor each image, extract the description, lighting, mood, and dominant colors."
        )
        
        content_list = [{"type": "text", "text": prompt_text}]
        
        for p in batch_paths:
            try:
                mime_type = get_image_mime_type(p)
                base64_data = encode_image_to_base64(p)
                content_list.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mime_type};base64,{base64_data}"
                    }
                })
            except Exception as e:
                print(f"Error encoding image {p}: {e}")
                # We still want to proceed, but mock or log
        
        # Build schema guidelines to append to system instructions
        schema_json = json.dumps(ImageAnalysisBatch.model_json_schema(), indent=2)
        system_prompt = (
            "You are a vision-language assistant. You must analyze the provided images "
            "and output a single JSON object matching this schema:\n"
            f"{schema_json}\n"
            "Return ONLY the JSON object. Do not enclose it in any formatting or markdown blocks."
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content_list}
        ]
        
        try:
            # Call the NVIDIA NIM vision model
            raw_response = call_nvidia_chat(
                model=model,
                messages=messages,
                json_mode=False,
                temperature=0.2
            )
            
            # Extract JSON substring from the response
            json_str = extract_json_from_text(raw_response)
            
            # Parse the response into Pydantic
            batch_result = ImageAnalysisBatch.model_validate_json(json_str)
            
            # Map the analyses to the actual image paths
            for idx, analysis in enumerate(batch_result.analyses):
                if idx < len(batch_paths):
                    # Ensure path and filename are correctly set in the state
                    analysis.image_path = os.path.abspath(batch_paths[idx])
                    analysis.filename = filenames[idx]
                    analyses.append(analysis)
                    print(f"Successfully analyzed: {analysis.filename}")
                    print(f" - Mood: {analysis.mood} | Desc: {analysis.description[:80]}...")
                
        except Exception as e:
            print(f"Error analyzing batch: {e}. Falling back to default descriptions.")
            # Fallback mock analysis so the pipeline doesn't crash
            for idx, p in enumerate(batch_paths):
                fname = filenames[idx]
                fallback = ImageAnalysis(
                    image_path=os.path.abspath(p),
                    filename=fname,
                    description=f"An event photo showing a scene ({fname})",
                    lighting="neutral",
                    mood="celebratory",
                    dominant_colors=["gray", "white"]
                )
                analyses.append(fallback)
                print(f"Fallback generated for: {fname}")



    state["image_analyses"] = analyses
    state["status"] = "images_analyzed"
    return state
