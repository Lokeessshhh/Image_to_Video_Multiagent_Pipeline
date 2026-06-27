import os
import pytest
from unittest.mock import patch, MagicMock
from pipeline.graph import create_pipeline_graph
from pipeline.state import PipelineState, VideoIntent, Storyboard, StoryboardScene, ImageAnalysis

# Create a mock image file to avoid errors in tests
@pytest.fixture
def mock_images(tmp_path):
    images = []
    for i in range(7):
        p = tmp_path / f"test_photo_{i}.jpg"
        p.write_bytes(b"dummy image content")
        images.append(str(p))
    return images

@patch("pipeline.agents.intent_parser.call_groq_structured")
def test_intent_parser(mock_call):
    # Setup mock
    mock_intent = VideoIntent(
        pacing="slow",
        visual_style="Cinematic wedding",
        caption_tone="emotional",
        transition_preference="crossfade",
        music_tempo="slow"
    )
    mock_call.return_value = mock_intent
    
    from pipeline.agents.intent_parser import parse_intent
    
    state: PipelineState = {
        "user_prompt": "cinematic wedding reel, slow and emotional",
        "image_paths": [],
        "video_intent": None,
        "image_analyses": [],
        "storyboard": None,
        "remotion_code": "",
        "compile_errors": [],
        "retry_count": 0,
        "status": "starting",
        "error_report": None
    }
    
    new_state = parse_intent(state)
    assert new_state["status"] == "intent_parsed"
    assert new_state["video_intent"] is not None
    assert new_state["video_intent"].pacing == "slow"
    mock_call.assert_called_once()

@patch("pipeline.agents.image_analyser.call_nvidia_chat")
def test_image_analyser(mock_nvidia, mock_images):
    # Mocking response for 7 images (will be 2 batches: 5 then 2)
    mock_json_batch1 = """{
      "analyses": [
        {"image_path": "path1", "filename": "test_photo_0.jpg", "description": "Happy couple smiling", "lighting": "warm", "mood": "joyful", "dominant_colors": ["pink", "white"]},
        {"image_path": "path2", "filename": "test_photo_1.jpg", "description": "Wedding cake detail", "lighting": "soft", "mood": "elegant", "dominant_colors": ["gold", "white"]},
        {"image_path": "path3", "filename": "test_photo_2.jpg", "description": "Dancing guests", "lighting": "dim", "mood": "energetic", "dominant_colors": ["purple", "blue"]},
        {"image_path": "path4", "filename": "test_photo_3.jpg", "description": "Rings macro shot", "lighting": "sparkling", "mood": "romantic", "dominant_colors": ["gold", "silver"]},
        {"image_path": "path5", "filename": "test_photo_4.jpg", "description": "Couple walking at sunset", "lighting": "sunset", "mood": "romantic", "dominant_colors": ["orange", "warm yellow"]}
      ]
    }"""
    mock_json_batch2 = """{
      "analyses": [
        {"image_path": "path6", "filename": "test_photo_5.jpg", "description": "Bride getting ready", "lighting": "bright", "mood": "calm", "dominant_colors": ["white", "cream"]},
        {"image_path": "path7", "filename": "test_photo_6.jpg", "description": "Sparkler sendoff", "lighting": "warm sparkler glow", "mood": "celebratory", "dominant_colors": ["orange", "black"]}
      ]
    }"""
    
    mock_nvidia.side_effect = [mock_json_batch1, mock_json_batch2]
    
    from pipeline.agents.image_analyser import analyze_images
    
    state: PipelineState = {
        "user_prompt": "cinematic wedding",
        "image_paths": mock_images,
        "video_intent": None,
        "image_analyses": [],
        "storyboard": None,
        "remotion_code": "",
        "compile_errors": [],
        "retry_count": 0,
        "status": "starting",
        "error_report": None
    }
    
    with patch.dict("os.environ", {"NVIDIA_API_KEY": "fake_key"}):
        new_state = analyze_images(state)
        
    assert new_state["status"] == "images_analyzed"
    assert len(new_state["image_analyses"]) == 7
    assert mock_nvidia.call_count == 2  # Proves 5-image batching splits 7 images into 2 calls

@patch("pipeline.agents.storyboard_writer.call_groq_structured")
def test_storyboard_writer(mock_call):
    # Mocking storyboard writing output
    mock_storyboard = Storyboard(
        scenes=[
            StoryboardScene(image_path="path1", filename="test_photo_0.jpg", duration_frames=90, caption="The beautiful day begins", transition_type="crossfade", transition_duration_frames=15, zoom_animation="zoom_in"),
            StoryboardScene(image_path="path2", filename="test_photo_1.jpg", duration_frames=90, caption="Details of love", transition_type="crossfade", transition_duration_frames=15, zoom_animation="zoom_out"),
        ],
        total_duration_frames=180,
        narrative_arc="Start of the wedding and close up details."
    )
    mock_call.return_value = mock_storyboard
    
    from pipeline.agents.storyboard_writer import write_storyboard
    
    state: PipelineState = {
        "user_prompt": "cinematic wedding",
        "image_paths": [],
        "video_intent": VideoIntent(pacing="slow", visual_style="Cinematic", caption_tone="emotional", transition_preference="crossfade"),
        "image_analyses": [
            ImageAnalysis(image_path="path1", filename="test_photo_0.jpg", description="Desc1", lighting="light1", mood="mood1", dominant_colors=["color"]),
            ImageAnalysis(image_path="path2", filename="test_photo_1.jpg", description="Desc2", lighting="light2", mood="mood2", dominant_colors=["color"])
        ],
        "storyboard": None,
        "remotion_code": "",
        "compile_errors": [],
        "retry_count": 0,
        "status": "images_analyzed",
        "error_report": None
    }
    
    new_state = write_storyboard(state)
    assert new_state["status"] == "storyboard_written"
    assert new_state["storyboard"] is not None
    assert new_state["storyboard"].total_duration_frames == 165
    assert len(new_state["storyboard"].scenes) == 2

@patch("pipeline.agents.compiler_fixer.subprocess.run")
@patch("pipeline.agents.script_generator.call_groq_chat")
@patch("pipeline.agents.storyboard_writer.call_groq_structured")
@patch("pipeline.agents.image_analyser.call_groq_chat")
@patch("pipeline.agents.intent_parser.call_groq_structured")
@patch("shutil.copy")
def test_full_pipeline_compilation_retry(mock_copy, mock_intent, mock_analyse, mock_storyboard, mock_script, mock_sub_run, mock_images):
    """
    Simulates a full pipeline run with a compilation failure on the first pass
    and a compilation success on the second pass.
    Ensures LangGraph loops correctly and fixes the script.
    """
    # 1. Intent Parser Mock
    mock_intent.return_value = VideoIntent(pacing="slow", visual_style="cinematic", caption_tone="soft", transition_preference="crossfade")
    
    # 2. Image Analyser Mock
    mock_analyse.return_value = """{
      "analyses": [
        {"image_path": "path1", "filename": "test_photo_0.jpg", "description": "Couples laughing", "lighting": "warm", "mood": "happy", "dominant_colors": ["white", "green"]}
      ]
    }"""
    
    # 3. Storyboard Mock
    mock_storyboard.return_value = Storyboard(
        scenes=[
            StoryboardScene(image_path="path1", filename="test_photo_0.jpg", duration_frames=90, caption="Sweet laugh", transition_type="crossfade", transition_duration_frames=15, zoom_animation="zoom_in")
        ],
        total_duration_frames=90,
        narrative_arc="A single happy scene."
    )
    
    # 4. Script Generator Mock (runs twice: once for initial, once for fix)
    mock_script.side_effect = [
        "const MainVideo = () => { invalid syntax here }",  # Bad code first
        "export const MainVideo = () => { return <div>Valid Code</div> }" # Fixed code second
    ]
    
    # 5. Subprocess Compile Run Mock (runs twice)
    # First call fails (returns non-zero), second call succeeds (returns zero)
    mock_process_fail = MagicMock()
    mock_process_fail.returncode = 1
    mock_process_fail.stdout = "TypeScript Error: Syntax error at line 1"
    mock_process_fail.stderr = ""
    
    mock_process_success = MagicMock()
    mock_process_success.returncode = 0
    
    mock_sub_run.side_effect = [
        mock_process_fail,    # Typecheck 1 fails
        mock_process_success, # Typecheck 2 succeeds
        mock_process_success  # Render command succeeds
    ]
    
    # Mocking os.path.exists, os.makedirs, and builtins.open
    from unittest.mock import mock_open
    with patch("os.path.exists", return_value=True), \
         patch("os.makedirs"), \
         patch("builtins.open", mock_open()):
        # Create pipeline graph
        graph = create_pipeline_graph()
        
        initial_state = {
            "user_prompt": "Cinematic slow wedding reel",
            "image_paths": mock_images[:1],
            "video_intent": None,
            "image_analyses": [],
            "storyboard": None,
            "remotion_code": "",
            "compile_errors": [],
            "retry_count": 0,
            "status": "starting",
            "error_report": None
        }
        
        # Execute the compiled graph
        final_state = graph.invoke(initial_state)
        
        # Assertions
        assert final_state["status"] == "completed"  # Completed means rendered successfully!
        assert final_state["retry_count"] == 1       # Verified we retried exactly once!
        assert len(final_state["compile_errors"]) == 1 # Verified the compiler logged the error!
        assert "TypeScript Error" in final_state["compile_errors"][0]
        
        # Script generator should have been called twice (initial + fix)
        assert mock_script.call_count == 2
        # Compiler & Fixer typecheck should have run twice
        assert mock_sub_run.call_count == 3  # 2 typechecks + 1 render
