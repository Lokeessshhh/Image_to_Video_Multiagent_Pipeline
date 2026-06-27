from langgraph.graph import StateGraph, END
from pipeline.state import PipelineState
from pipeline.agents.intent_parser import parse_intent
from pipeline.agents.image_analyser import analyze_images
from pipeline.agents.storyboard_writer import write_storyboard
from pipeline.agents.script_generator import generate_script
from pipeline.agents.compiler_fixer import compile_and_fix
from pipeline.agents.renderer import render_video

def route_compilation(state: PipelineState) -> str:
    """
    Decides where the pipeline should go next after compilation check.
    - If compiled successfully: go to renderer.
    - If compilation failed (retry < max): go back to script generator.
    - If compilation failed (max retries exceeded): exit to END.
    """
    status = state.get("status")
    if status == "compiled":
        return "renderer"
    elif status == "compilation_failed":
        return "script_generator"
    else:
        # Fails or other terminal states
        return END

def create_pipeline_graph():
    # Initialize the state graph
    builder = StateGraph(PipelineState)
    
    # Register nodes
    builder.add_node("intent_parser", parse_intent)
    builder.add_node("image_analyser", analyze_images)
    builder.add_node("storyboard_writer", write_storyboard)
    builder.add_node("script_generator", generate_script)
    builder.add_node("compiler_fixer", compile_and_fix)
    builder.add_node("renderer", render_video)
    
    # Set entry point
    builder.set_entry_point("intent_parser")
    
    # Sequential edges
    builder.add_edge("intent_parser", "image_analyser")
    builder.add_edge("image_analyser", "storyboard_writer")
    builder.add_edge("storyboard_writer", "script_generator")
    builder.add_edge("script_generator", "compiler_fixer")
    
    # Conditional routing edge from compiler_fixer
    builder.add_conditional_edges(
        "compiler_fixer",
        route_compilation,
        {
            "renderer": "renderer",
            "script_generator": "script_generator",
            END: END
        }
    )
    
    # Edge from renderer to end
    builder.add_edge("renderer", END)
    
    # Compile graph
    return builder.compile()
