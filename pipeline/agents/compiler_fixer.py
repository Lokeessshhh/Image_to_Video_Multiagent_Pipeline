import os
import subprocess
from pipeline.state import PipelineState

def compile_and_fix(state: PipelineState) -> PipelineState:
    """
    Compiles the generated Remotion composition using 'npx tsc --noEmit'.
    If compile fails, catches the compiler errors and saves them in the state.
    Increments the retry count and routes back to the script generator if under the limit.
    """
    print(f"\n--- [5/5] Running Compiler & Fixer ---")
    
    project_dir = os.path.abspath("video-project")
    print(f"Running TypeScript typecheck in: {project_dir}")
    
    # Check if node_modules exists, if not, try to run npm install first
    if not os.path.exists(os.path.join(project_dir, "node_modules")):
        print("node_modules not found. Running npm install first...")
        try:
            subprocess.run("npm install", shell=True, cwd=project_dir, check=True, stdout=subprocess.DEVNULL)
            print("npm install completed.")
        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to run npm install inside video-project: {e}"
            print(error_msg)
            state["compile_errors"].append(error_msg)
            state["status"] = "failed"
            state["error_report"] = {
                "phase": "npm_install",
                "error": error_msg
            }
            return state

    # Run npx tsc --noEmit to typecheck the project
    result = subprocess.run(
        "npx tsc --noEmit",
        shell=True,
        cwd=project_dir,
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("Compilation succeeded! Code is type-safe and ready to render.")
        state["status"] = "compiled"
        return state
    else:
        # Compilation failed
        error_output = result.stderr + "\n" + result.stdout
        print(f"Compilation FAILED with exit code {result.returncode}.")
        print("Captured Compiler Errors:")
        
        # Keep only the first 1000 characters of error logs to avoid overflowing context window
        clean_errors = error_output.strip()
        print(clean_errors[:500] + "\n..." if len(clean_errors) > 500 else clean_errors)
        
        # Save to state
        state["compile_errors"].append(clean_errors)
        state["retry_count"] += 1
        
        max_retries = 3
        if state["retry_count"] >= max_retries:
            print(f"Reached max retry limit ({max_retries}). Exiting with failure.")
            state["status"] = "failed"
            state["error_report"] = {
                "phase": "typecheck",
                "retry_count": state["retry_count"],
                "errors": state["compile_errors"],
                "last_error": clean_errors,
                "message": "Failed to compile the script after maximum retries."
            }
        else:
            print(f"Routing back to Script Generator for retry #{state['retry_count']}...")
            state["status"] = "compilation_failed"
            
        return state
