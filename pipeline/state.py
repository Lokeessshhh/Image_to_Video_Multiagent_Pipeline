from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

class VideoIntent(BaseModel):
    pacing: str = Field(description="Pacing style: slow, moderate, or fast")
    visual_style: str = Field(description="Visual theme description, e.g., cinematic, corporate, upbeat, emotional")
    caption_tone: str = Field(description="Tone of the text captions: emotional, professional, bold, simple, etc.")
    transition_preference: str = Field(description="Preferred transition style: crossfade, slide-left, cut, fade, etc.")
    music_tempo: Optional[str] = Field(default="moderate", description="Music tempo description")

class ImageAnalysis(BaseModel):
    image_path: str = Field(description="Absolute path to the image file")
    filename: str = Field(description="Name of the image file")
    description: str = Field(description="Detailed visual description of what is happening in the photo")
    lighting: str = Field(description="Lighting characteristics (e.g. warm, cold, dramatic, bright)")
    mood: str = Field(description="Emotional mood of the image (e.g. romantic, joyful, serious, energetic)")
    dominant_colors: List[str] = Field(description="List of 2-3 dominant colors in the photo")

class StoryboardScene(BaseModel):
    image_path: str = Field(description="Path to the image used in this scene")
    filename: str = Field(description="Filename of the image")
    duration_frames: int = Field(description="Duration in frames this scene is visible (at 30fps, 30 frames = 1s)")
    caption: str = Field(description="Subtitled text overlay for this scene")
    transition_type: str = Field(description="Transition style to next scene: crossfade, slide, cut, zoom")
    transition_duration_frames: int = Field(description="Duration of transition in frames (e.g. 15 frames = 0.5s)")
    zoom_animation: str = Field(description="Animation effect for this scene's image: zoom_in, zoom_out, pan_left, pan_right, or static")

class Storyboard(BaseModel):
    scenes: List[StoryboardScene] = Field(description="Ordered list of scenes in the video")
    total_duration_frames: int = Field(description="Total duration of the composition in frames")
    narrative_arc: str = Field(description="Brief description of the narrative flow of the selected scenes")

class PipelineState(TypedDict):
    user_prompt: str
    image_paths: List[str]
    video_intent: Optional[VideoIntent]
    image_analyses: List[ImageAnalysis]
    storyboard: Optional[Storyboard]
    remotion_code: str
    compile_errors: List[str]
    retry_count: int
    status: str
    error_report: Optional[Dict[str, Any]]
    category: str
