import os
import sys
import argparse
import json
import shutil
from dotenv import load_dotenv
from rich import print as rprint
from rich.panel import Panel

# Load environment variables from .env
load_dotenv()

# Verify that API keys are set
if not os.getenv("GROQ_API_KEY"):
    rprint("[yellow]Warning: GROQ_API_KEY is not set in environment or .env. Pipeline calls will fail unless keys are configured.[/yellow]")

from pipeline.graph import create_pipeline_graph
from pipeline.state import PipelineState

def run_pipeline(prompt: str, images_dir: str, max_retries: int = 3):
    rprint(Panel(f"[bold green]FotoOwl Image-to-Video Multiagent Pipeline[/bold green]\n"
                 f"Prompt: [cyan]'{prompt}'[/cyan]\n"
                 f"Images Directory: [cyan]'{images_dir}'[/cyan]",
                 title="Initializing Pipeline"))
    
    # 1. Gather input images
    if not os.path.exists(images_dir):
        rprint(f"[red]Error: Images directory '{images_dir}' does not exist.[/red]")
        sys.exit(1)
        
    image_extensions = (".jpg", ".jpeg", ".png", ".webp")
    image_files = [
        os.path.join(images_dir, f)
        for f in os.listdir(images_dir)
        if f.lower().endswith(image_extensions)
    ]
    
    if not image_files:
        rprint(f"[red]Error: No images with extensions {image_extensions} found in '{images_dir}'.[/red]")
        sys.exit(1)
    rprint(f"Found {len(image_files)} source images in the directory.")
    if len(image_files) > 8:
        rprint(f"[yellow]Selecting a subset of 8 images to process (complying with the 8-12 image reel brief).[/yellow]")
        image_files = image_files[:8]
        
    # Convert image files to absolute paths for consistency
    abs_image_paths = [os.path.abspath(f) for f in image_files]
    
    category = os.path.basename(os.path.normpath(images_dir)) or "default"
    
    # 2. Build initial state
    initial_state = {
        "user_prompt": prompt,
        "image_paths": abs_image_paths,
        "video_intent": None,
        "image_analyses": [],
        "storyboard": None,
        "remotion_code": "",
        "compile_errors": [],
        "retry_count": 0,
        "status": "starting",
        "error_report": None,
        "category": category
    }
    
    # 3. Create and compile LangGraph StateGraph
    rprint("[bold blue]Orchestrating agent graph...[/bold blue]")
    graph = create_pipeline_graph()
    
    # Write the graph representation as a mermaid diagram to README or file (optional check)
    output_dir = os.path.join("output", category)
    os.makedirs(output_dir, exist_ok=True)
    try:
        mermaid_png = graph.get_graph().draw_mermaid_png()
        with open(os.path.join(output_dir, "graph_diagram.png"), "wb") as f:
            f.write(mermaid_png)
        rprint(f"[green]Saved pipeline graph diagram to {os.path.join(output_dir, 'graph_diagram.png')}[/green]")
    except Exception as e:
        rprint(f"[yellow]Could not draw graph diagram: {e} (skipping graph image export)[/yellow]")
    
    # 4. Invoke graph
    rprint("[bold blue]Executing multiagent pipeline nodes...[/bold blue]")
    final_state = graph.invoke(initial_state)
    
    # 5. Handle outcomes
    status = final_state.get("status")
    
    # Save the final state to a JSON file (excluding large base64 contents/raw code to keep it readable)
    clean_state = {
        "user_prompt": final_state.get("user_prompt"),
        "image_paths_count": len(final_state.get("image_paths", [])),
        "video_intent": final_state.get("video_intent").model_dump() if final_state.get("video_intent") else None,
        "image_analyses_count": len(final_state.get("image_analyses", [])),
        "storyboard": final_state.get("storyboard").model_dump() if final_state.get("storyboard") else None,
        "compile_errors": final_state.get("compile_errors", []),
        "retry_count": final_state.get("retry_count", 0),
        "status": status,
        "error_report": final_state.get("error_report"),
        "category": category
    }
    
    state_path = os.path.join(output_dir, "pipeline_state.json")
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(clean_state, f, indent=2)
    rprint(f"[green]Saved final pipeline state to: {state_path}[/green]")

    # Save storyboard specifically
    if final_state.get("storyboard"):
        storyboard_path = os.path.join(output_dir, "storyboard.json")
        # Also copy it to video-project/src/storyboard.json so Remotion has it
        project_storyboard_path = "video-project/src/storyboard.json"
        
        storyboard_dump = final_state.get("storyboard").model_dump()
        
        with open(storyboard_path, "w", encoding="utf-8") as f:
            json.dump(storyboard_dump, f, indent=2)
            
        with open(project_storyboard_path, "w", encoding="utf-8") as f:
            json.dump(storyboard_dump, f, indent=2)
            
        rprint(f"[green]Saved storyboard JSON to: {storyboard_path}[/green]")
        
    # Save generated code specifically
    if final_state.get("remotion_code"):
        code_path = os.path.join(output_dir, "Composition.tsx")
        with open(code_path, "w", encoding="utf-8") as f:
            f.write(final_state.get("remotion_code"))
        rprint(f"[green]Saved final composition TSX script to: {code_path}[/green]")
        
    if status == "completed":
        rprint(Panel(f"[bold green]Success![/bold green] Video successfully compiled and rendered end-to-end.\n"
                     f"You can find the output MP4 at: [cyan]{os.path.join(output_dir, 'video.mp4')}[/cyan]",
                     title="Pipeline Completed"))
    else:
        rprint(Panel(f"[bold red]Pipeline Failed![/bold red] Current state status: [cyan]{status}[/cyan]\n"
                     f"Error Details: {json.dumps(final_state.get('error_report'), indent=2)}",
                     title="Pipeline Failed"))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Orchestrate FotoOwl Image-to-Video Multiagent Pipeline.")
    parser.add_argument(
        "--prompt",
        default="Cinematic wedding reel, slow and emotional, warm tones, minimal text",
        help="Creative brief text outlining video styling"
    )
    parser.add_argument(
        "--images-dir",
        default="input_images",
        help="Local directory path containing the event photos"
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Max retries for compiler fix node"
    )
    
    args = parser.parse_args()
    run_pipeline(args.prompt, args.images_dir, args.max_retries)
