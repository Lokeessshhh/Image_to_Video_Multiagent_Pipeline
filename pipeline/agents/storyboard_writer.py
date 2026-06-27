from pipeline.state import PipelineState, Storyboard
from pipeline.utils import call_groq_structured
from pipeline.rag.store import RagStore

def write_storyboard(state: PipelineState) -> PipelineState:
    """
    Retrieves style context via RAG based on the VideoIntent,
    and uses qwen/qwen3.6-27b to sequence the analyzed images into a coherent Storyboard.
    """
    print(f"\n--- [3/5] Running Storyboard Writer ---")
    
    intent = state.get("video_intent")
    analyses = state.get("image_analyses", [])
    
    if not intent:
        print("Error: No VideoIntent found in state!")
        return state
        
    if not analyses:
        print("Error: No image analyses found in state!")
        return state

    # Initialize RAG and retrieve relevant style guidelines
    print("Querying RAG for style guide...")
    store = RagStore()
    retrieved_style = store.retrieve_style(f"{intent.visual_style} {intent.pacing} pacing")
    print(f"Retrieved Style Context:\n{retrieved_style}\n")
    
    # Prepare the analysis description for the prompt
    analyses_str = ""
    for idx, a in enumerate(analyses):
        analyses_str += (
            f"Image [{idx}]:\n"
            f" - Filename: {a.filename}\n"
            f" - Path: {a.image_path}\n"
            f" - Description: {a.description}\n"
            f" - Mood: {a.mood}\n"
            f" - Lighting: {a.lighting}\n"
            f" - Colors: {', '.join(a.dominant_colors)}\n\n"
        )
        
    system_prompt = (
        "You are an expert Storyboard Writer. Your goal is to select a subset of the provided "
        "images (usually 5 to 8 images for a short reel) and sequence them to build a cohesive narrative arc. "
        "You must determine the timing (in frames at 30fps), transitions, animations, and overlays (captions) "
        "for each scene, based on the user's intent and retrieved style guide guidelines. Use the exact filenames "
        "and paths from the input list. Make sure the narrative makes logical sense and flows well."
    )
    
    user_prompt = (
        f"Client Video Intent:\n"
        f" - Pacing: {intent.pacing}\n"
        f" - Style: {intent.visual_style}\n"
        f" - Tone: {intent.caption_tone}\n"
        f" - Transition: {intent.transition_preference}\n\n"
        f"Retrieved Style Guide:\n"
        f"{retrieved_style}\n\n"
        f"Available Images for sequencing:\n"
        f"{analyses_str}\n"
        f"Please write a storyboard. Choose the best images, order them, and output a JSON matching the Storyboard schema."
    )
    
    # Call openai/gpt-oss-120b for high-quality structured storyboard generation
    storyboard = call_groq_structured(
        model="qwen/qwen3.6-27b",
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        response_model=Storyboard
    )
    
    # Calculate exact timeline duration in frames accounting for transition overlaps
    calc_total_frames = 0
    for idx, scene in enumerate(storyboard.scenes):
        if idx == 0:
            calc_total_frames = scene.duration_frames
        else:
            prev_overlap = storyboard.scenes[idx - 1].transition_duration_frames
            calc_total_frames += scene.duration_frames - prev_overlap
            
    storyboard.total_duration_frames = calc_total_frames
    
    print(f"Storyboard generated with {len(storyboard.scenes)} scenes. Total duration: {calc_total_frames} frames ({calc_total_frames/30:.2f}s).")
    
    # Ensure safe terminal print on Windows consoles (replaces non-ascii with '?')
    safe_arc = storyboard.narrative_arc.encode('ascii', 'replace').decode('ascii')
    print(f"Narrative Arc: '{safe_arc}'")
    for idx, scene in enumerate(storyboard.scenes):
        safe_caption = scene.caption.encode('ascii', 'replace').decode('ascii')
        print(f" Scene {idx+1}: {scene.filename} | Duration: {scene.duration_frames}f | Capt: '{safe_caption}' | Trans: {scene.transition_type}")
        
    state["storyboard"] = storyboard
    state["status"] = "storyboard_written"
    return state
