import os
import shutil
import subprocess
from pipeline.state import PipelineState

def render_video(state: PipelineState) -> PipelineState:
    """
    Triggers the final Remotion render to produce the MP4 video reel.
    Copies the rendered MP4 file to the main output directory.
    """
    print(f"\n--- Running Renderer ---")
    
    project_dir = os.path.abspath("video-project")
    category = state.get("category", "default")
    output_dir = os.path.abspath(os.path.join("output", category))
    os.makedirs(output_dir, exist_ok=True)
    
    target_mp4 = os.path.join(output_dir, "video.mp4")
    
    # 1. Run Remotion render
    # Standard: npx remotion render <composition-id> <output-file-path>
    # We render composition "my-video" to "out/video.mp4"
    command = "npx remotion render my-video out/video.mp4 --overwrite --concurrency=1"
    print(f"Executing: {command} in {project_dir}")
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=project_dir,
            capture_output=True,
            encoding="utf-8",
            errors="ignore",
            check=True
        )
        print("Rendering completed successfully!")
        
        # Copy the rendered video to the main output folder
        src_mp4 = os.path.join(project_dir, "out", "video.mp4")
        if os.path.exists(src_mp4):
            shutil.copy(src_mp4, target_mp4)
            print(f"Video saved to: {target_mp4}")
            state["status"] = "completed"
            # Add video path to state
            state["error_report"] = None
        else:
            raise FileNotFoundError(f"Rendered video file not found at: {src_mp4}")
            
    except subprocess.CalledProcessError as e:
        error_msg = f"Remotion render command failed: {e}\nSTDOUT: {e.stdout}\nSTDERR: {e.stderr}"
        safe_msg = error_msg.encode('ascii', 'replace').decode('ascii')
        print(safe_msg)
        state["status"] = "failed"
        state["error_report"] = {
            "phase": "render",
            "error": error_msg,
            "stdout": e.stdout,
            "stderr": e.stderr
        }
    except Exception as e:
        error_msg = f"Unexpected error during render copy: {e}"
        safe_msg = error_msg.encode('ascii', 'replace').decode('ascii')
        print(safe_msg)
        state["status"] = "failed"
        state["error_report"] = {
            "phase": "render_copy",
            "error": error_msg
        }
        
    return state
