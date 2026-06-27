from pipeline.state import PipelineState, VideoIntent
from pipeline.utils import call_groq_structured

def parse_intent(state: PipelineState) -> PipelineState:
    """
    Parses the raw user prompt into a structured VideoIntent object
    that dictates the pacing, transition preferences, and stylistic choices downstream.
    """
    print(f"\n--- [1/5] Running Intent Parser ---")
    user_prompt = state.get("user_prompt", "")
    print(f"Client Prompt: '{user_prompt}'")
    
    system_prompt = (
        "You are an expert Video Producer and Creative Director. "
        "Your task is to parse a client's video creation creative brief (prompt) into "
        "a structured VideoIntent object that specifies pacing, visual style, caption tone, "
        "and transition preferences. Make sensible defaults if a specific parameter is not explicitly mentioned, "
        "fitting the requested overall theme (e.g. upbeat, cinematic, corporate)."
    )
    
    user_prompt_instruction = f"Creative brief from user: '{user_prompt}'"
    
    # Call Groq with openai/gpt-oss-20b and Pydantic structured output
    video_intent = call_groq_structured(
        model="openai/gpt-oss-20b",
        system_prompt=system_prompt,
        user_prompt=user_prompt_instruction,
        response_model=VideoIntent
    )
    
    print(f"Parsed Video Intent:")
    print(f" - Pacing: {video_intent.pacing}")
    print(f" - Visual Style: {video_intent.visual_style}")
    print(f" - Caption Tone: {video_intent.caption_tone}")
    print(f" - Transitions: {video_intent.transition_preference}")
    print(f" - Music Tempo: {video_intent.music_tempo}")
    
    # Update state
    state["video_intent"] = video_intent
    state["status"] = "intent_parsed"
    return state
