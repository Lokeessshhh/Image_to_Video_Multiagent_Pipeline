import os
from pipeline.state import PipelineState
from pipeline.utils import call_groq_chat
from pipeline.rag.store import RagStore

def generate_script(state: PipelineState) -> PipelineState:
    """
    Generates or modifies video-project/src/Composition.tsx based on the storyboard and video intent.
    Retrieves Remotion API code snippets from RAG.
    If compile_errors exist, incorporates them to perform a targeted fix.
    """
    print(f"\n--- [4/5] Running Script Generator ---")
    
    intent = state.get("video_intent")
    storyboard = state.get("storyboard")
    errors = state.get("compile_errors", [])
    retry_count = state.get("retry_count", 0)
    
    if not storyboard or not intent:
        print("Error: Storyboard or VideoIntent missing in state.")
        return state

    # Copy storyboard images to public directory
    public_images_dir = os.path.join("video-project", "public", "images")
    os.makedirs(public_images_dir, exist_ok=True)
    import shutil
    for scene in storyboard.scenes:
        src = scene.image_path
        dst = os.path.join(public_images_dir, scene.filename)
        if os.path.exists(src):
            shutil.copy(src, dst)
            print(f"Copied {src} to {dst}")
        else:
            print(f"Warning: Storyboard image source not found at: {src}")

    # Initialize RAG store
    store = RagStore()
    
    # 1. Retrieve RAG documentation
    query_terms = ["Sequence", "staticFile", "interpolate"]
    if any(s.transition_type != "cut" for s in storyboard.scenes):
        query_terms.append("crossfade transition")
    if intent.pacing == "fast" or any(s.zoom_animation != "static" for s in storyboard.scenes):
        query_terms.append("spring animation")
        
    rag_query = " ".join(query_terms)
    print(f"Querying Remotion API RAG store with: '{rag_query}'")
    retrieved_api = store.retrieve_api(rag_query, n_results=3)
    
    # If this is a retry due to compilation errors, retrieve error-related docs
    error_context = ""
    if errors:
        latest_error = errors[-1]
        print(f"Compilation feedback loop active (Retry #{retry_count}). Latest error:\n{latest_error[:200]}...")
        # Query RAG using the error message
        retrieved_error_docs = store.retrieve_api(latest_error, n_results=1)
        error_context = (
            f"\n=== COMPILATION ERROR FEEDBACK (FIX THIS) ===\n"
            f"Your previous code failed compilation with the following error:\n"
            f"{latest_error}\n\n"
            f"Here is some relevant Remotion documentation that might help solve this error:\n"
            f"{retrieved_error_docs}\n"
            f"=============================================\n"
        )

    # 2. Build the LLM prompts
    system_prompt = (
        "You are an expert Frontend Developer and Remotion Video Programmer. "
        "Your task is to write a single, syntactically correct TypeScript React file (Composition.tsx) "
        "that implements the provided storyboard. The file MUST export a React component named 'MainVideo' "
        "as a named export:\n"
        "export const MainVideo: React.FC = () => { ... }\n\n"
        "Strict rules for your code:\n"
        "1. Do not use external libraries other than 'react', 'remotion', and '@remotion/transitions' or '@remotion/shapes'. Do NOT use the `<Composition>` tag in this file. Import `AbsoluteFill`, `Sequence`, `interpolate`, `useCurrentFrame`, and `staticFile` directly from `'remotion'`. Do NOT import nonexistent objects like `Transition` from `@remotion/transitions`.\n"
        "2. Do not use Tailwind CSS. Write clean inline CSS styles.\n"
        "3. **Dynamic Storyboard Import**: Import the storyboard scenes dynamically from './storyboard.json':\n"
        "   `import storyboard from './storyboard.json';`\n"
        "   Do NOT hardcode filenames, captions, or durations in the file. Read them dynamically by mapping over `storyboard.scenes`!\n"
        "4. Calculate start frames dynamically: Slide 0 starts at 0. Slide N starts at: (start of Slide N-1) + (duration of Slide N-1) - (transition overlap of Slide N-1). You MUST calculate these start frames *before* the return statement (e.g., in a loop, reduce, or map before rendering, or using a pre-computed array). Do NOT put any increment code (like `startFrame += ...`) after a `return` statement in a `.map()` callback, as it becomes unreachable dead code. Always specify `{ extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }` on all `interpolate` calls to prevent negative or out-of-bound values from causing flashing/flickering in Remotion. **Safe Interpolate Helper**: Define a typed helper function at the top of the file to wrap Remotion's `interpolate` and prevent `inputRange must be strictly monotonically increasing` errors:\n"
        "   `const safeInterpolate = (value: number, inputRange: number[], outputRange: number[], options?: { extrapolateLeft?: 'clamp' | 'extend'; extrapolateRight?: 'clamp' | 'extend' }) => {\n"
        "     if (inputRange[0] === inputRange[1]) return outputRange[0];\n"
        "     return interpolate(value, inputRange, outputRange, options);\n"
        "   };\n"
        "   Use this helper everywhere instead of calling Remotion's `interpolate` directly.\n"
        "5. Reference images stored in public directory using the `staticFile(\"images/\" + scene.filename)` helper, NOT direct imports.\n"
        "6. **Premium Slide Layout**: To prevent faces/subjects from being cut off in vertical/portrait/cropped photos, design the Slide component to overlay two image tags: a background blurred image (styled with `position: 'absolute', width: '100%', height: '100%', objectFit: 'cover', filter: 'blur(20px) brightness(0.4)'`) and a foreground clean image (styled with `position: 'relative', height: '100%', maxWidth: '100%', objectFit: 'contain'`). The parent container wrapping these elements MUST center the foreground image horizontally and vertically using Flexbox: `{ display: 'flex', justifyContent: 'center', alignItems: 'center', position: 'relative', width: '100%', height: '100%', overflow: 'hidden' }`. Apply a subtle dark gradient at the bottom of the slide to ensure caption readability.\n"
        "7. **Storyboard JSON Interface**: The `storyboard.json` matches this interface. Use these exact field names:\n"
        "   interface StoryboardScene {\n"
        "     image_path: string;\n"
        "     filename: string;\n"
        "     duration_frames: number;\n"
        "     caption: string;\n"
        "     transition_type: string;\n"
        "     transition_duration_frames: number;\n"
        "     zoom_animation: string;\n"
        "   }\n"
        "   interface Storyboard {\n"
        "     scenes: StoryboardScene[];\n"
        "     total_duration_frames: number;\n"
        "     narrative_arc: string;\n"
        "   }\n"
        "8. **Remotion Frame Scopes**: Inside a component rendered inside a `<Sequence>` tag (e.g. `Slide`), the `useCurrentFrame()` hook already returns the local frame relative to the sequence start (starting at 0). Do NOT subtract the sequence start frame (`start`) from it. Simply use the value of `useCurrentFrame()` directly as the local frame.\n"
        "9. Do not include any explanation, intro text, or markdown code blocks (```tsx) in your output. Return ONLY the raw TypeScript React code."
    )

    scenes_str = ""
    for idx, scene in enumerate(storyboard.scenes):
        scenes_str += (
            f"Scene {idx+1}:\n"
            f" - Image Filename: {scene.filename}\n"
            f" - Caption: '{scene.caption}'\n"
            f" - Duration: {scene.duration_frames} frames\n"
            f" - Transition: {scene.transition_type} (duration {scene.transition_duration_frames}f)\n"
            f" - Zoom/Pan Animation: {scene.zoom_animation}\n\n"
        )

    user_prompt = (
        f"Creative Video Intent:\n"
        f" - Theme: {intent.visual_style}\n"
        f" - Pacing: {intent.pacing}\n"
        f" - Caption Tone: {intent.caption_tone}\n"
        f" - Transition preference: {intent.transition_preference}\n\n"
        f"Storyboard definition:\n"
        f"{scenes_str}\n"
        f"Total duration of video: {storyboard.total_duration_frames} frames\n\n"
        f"Retrieved Remotion API guidelines:\n"
        f"{retrieved_api}\n"
        f"{error_context}\n"
        f"Generate the complete Composition.tsx code now. Remember: ONLY the code, no markdown blocks."
    )

    # 3. Call openai/gpt-oss-120b for coding
    print("Generating Composition.tsx using openai/gpt-oss-120b...")
    remotion_code = call_groq_chat(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        json_mode=False,
        temperature=0.1
    )

    # Strip markdown backticks if the model ignored instructions
    code_cleaned = remotion_code.strip()
    if code_cleaned.startswith("```"):
        # Remove starting ```tsx or ```
        lines = code_cleaned.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines[-1].startswith("```"):
            lines = lines[:-1]
        code_cleaned = "\n".join(lines).strip()

    # Write code to file
    output_path = "video-project/src/Composition.tsx"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(code_cleaned)
        
    print(f"Composition.tsx successfully written ({len(code_cleaned)} bytes).")
    
    # Save the generated code in state
    state["remotion_code"] = code_cleaned
    state["status"] = "script_generated"
    return state
