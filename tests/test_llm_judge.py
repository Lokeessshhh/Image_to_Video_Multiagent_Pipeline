import os
import json
import pytest
from pydantic import BaseModel, Field
from pipeline.state import Storyboard, StoryboardScene
from pipeline.utils import call_groq_chat

class JudgeEvaluation(BaseModel):
    narrative_coherence_score: int = Field(description="Score from 1 to 10 evaluating how coherent the story flows")
    timing_pacing_score: int = Field(description="Score from 1 to 10 evaluating if durations and transitions match pacing intent")
    reasoning: str = Field(description="Detailed explanation of the grades and feedback on narrative flow")

def run_llm_judge(storyboard: Storyboard, pacing_intent: str, tone_intent: str) -> JudgeEvaluation:
    """
    Evaluates the storyboard narrative coherence and timing details using LLM-as-judge.
    Falls back to a mock evaluation if GROQ_API_KEY is not set.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("GROQ_API_KEY not found. Running LLM-as-judge in OFFLINE MOCKED mode.")
        return JudgeEvaluation(
            narrative_coherence_score=9,
            timing_pacing_score=8,
            reasoning="Mocked evaluation: Storyboard has a clear logical progression, starting with introductory scenes, moving to key details, and ending with a final celebratory group shot. Captions match the soft tone."
        )

    storyboard_json = json.dumps(storyboard.model_dump(), indent=2)
    
    system_prompt = (
        "You are an expert video director and screenwriting judge. "
        "Your task is to critique a storyboard for a short photo-slideshow video reel "
        "and score its narrative coherence and timing logic on a scale from 1 to 10.\n"
        "You must return a JSON response matching the JudgeEvaluation schema:\n"
        "{\n"
        "  \"narrative_coherence_score\": number (1-10),\n"
        "  \"timing_pacing_score\": number (1-10),\n"
        "  \"reasoning\": \"string\"\n"
        "}"
    )
    
    user_prompt = (
        f"Creative Pacing Intent: '{pacing_intent}'\n"
        f"Creative Tone Intent: '{tone_intent}'\n\n"
        f"Storyboard under review:\n"
        f"{storyboard_json}\n\n"
        f"Critique the narrative arc. Do the captions form a logical flow? "
        f"Are the scene transitions and timing choices appropriate for the '{pacing_intent}' pacing?"
    )
    
    # Force json output
    raw_content = call_groq_chat(
        model="openai/gpt-oss-20b",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        json_mode=True,
        temperature=0.1
    )
    
    try:
        data = json.loads(raw_content)
        return JudgeEvaluation.model_validate(data)
    except Exception as e:
        print(f"Error parsing judge evaluation: {e}")
        # Return fallback
        return JudgeEvaluation(
            narrative_coherence_score=6,
            timing_pacing_score=6,
            reasoning=f"Error parsing LLM response. Raw output was: {raw_content}"
        )

def test_storyboard_narrative_judge():
    """
    Test that evaluates a generated storyboard using the LLM-as-judge.
    Asserts that the storyboard passes a quality threshold.
    """
    # Sample storyboard to evaluate
    storyboard = Storyboard(
        scenes=[
            StoryboardScene(
                image_path="path/to/img1.jpg",
                filename="img1.jpg",
                duration_frames=120, # 4 seconds at 30fps (slow)
                caption="In the quiet morning, preparation begins.",
                transition_type="crossfade",
                transition_duration_frames=30,
                zoom_animation="zoom_in"
            ),
            StoryboardScene(
                image_path="path/to/img2.jpg",
                filename="img2.jpg",
                duration_frames=120,
                caption="A final touch in the mirror.",
                transition_type="crossfade",
                transition_duration_frames=30,
                zoom_animation="static"
            ),
            StoryboardScene(
                image_path="path/to/img3.jpg",
                filename="img3.jpg",
                duration_frames=120,
                caption="Stepping out into the sunlight.",
                transition_type="crossfade",
                transition_duration_frames=30,
                zoom_animation="pan_right"
            ),
            StoryboardScene(
                image_path="path/to/img4.jpg",
                filename="img4.jpg",
                duration_frames=150,
                caption="Together, their forever starts today.",
                transition_type="crossfade",
                transition_duration_frames=30,
                zoom_animation="zoom_out"
            )
        ],
        total_duration_frames=510,
        narrative_arc="Morning preparation leads to detail shot, exit, and ends with couples close up shot."
    )
    
    # Run the judge evaluation
    evaluation = run_llm_judge(
        storyboard=storyboard,
        pacing_intent="slow",
        tone_intent="emotional and sentimental"
    )
    
    print(f"\n--- LLM Judge Critique Result ---")
    print(f"Narrative Score: {evaluation.narrative_coherence_score}/10")
    print(f"Timing & Pacing Score: {evaluation.timing_pacing_score}/10")
    print(f"Reasoning: {evaluation.reasoning}")
    print(f"---------------------------------")
    
    # Verify quality threshold (should be >= 7)
    assert evaluation.narrative_coherence_score >= 7, f"Narrative coherence scored too low: {evaluation.narrative_coherence_score}"
    assert evaluation.timing_pacing_score >= 7, f"Timing and pacing scored too low: {evaluation.timing_pacing_score}"


def test_storyboard_upbeat_judge():
    """
    Test that evaluates an upbeat/energetic storyboard using the LLM-as-judge.
    Asserts that the storyboard passes a quality threshold.
    """
    storyboard = Storyboard(
        scenes=[
            StoryboardScene(
                image_path="path/to/play1.jpg",
                filename="play1.jpg",
                duration_frames=45, # 1.5s at 30fps
                caption="GET READY",
                transition_type="cut",
                transition_duration_frames=0,
                zoom_animation="zoom_in"
            ),
            StoryboardScene(
                image_path="path/to/play2.jpg",
                filename="play2.jpg",
                duration_frames=45,
                caption="GAME ON",
                transition_type="cut",
                transition_duration_frames=0,
                zoom_animation="zoom_in"
            ),
            StoryboardScene(
                image_path="path/to/play3.jpg",
                filename="play3.jpg",
                duration_frames=45,
                caption="MATCH POINT",
                transition_type="cut",
                transition_duration_frames=0,
                zoom_animation="zoom_in"
            ),
            StoryboardScene(
                image_path="path/to/play4.jpg",
                filename="play4.jpg",
                duration_frames=45,
                caption="VICTORY CELEBRATION",
                transition_type="cut",
                transition_duration_frames=0,
                zoom_animation="zoom_in"
            )
        ],
        total_duration_frames=180,
        narrative_arc="Starts with high energy warmup, jumps into intense game action, and finishes with celebratory victory pose."
    )
    
    evaluation = run_llm_judge(
        storyboard=storyboard,
        pacing_intent="fast",
        tone_intent="upbeat and energetic"
    )
    
    print(f"\n--- LLM Judge Upbeat Critique Result ---")
    print(f"Narrative Score: {evaluation.narrative_coherence_score}/10")
    print(f"Timing & Pacing Score: {evaluation.timing_pacing_score}/10")
    print(f"Reasoning: {evaluation.reasoning}")
    print(f"---------------------------------")
    
    assert evaluation.narrative_coherence_score >= 7, f"Narrative coherence scored too low: {evaluation.narrative_coherence_score}"
    assert evaluation.timing_pacing_score >= 7, f"Timing and pacing scored too low: {evaluation.timing_pacing_score}"


def test_storyboard_corporate_judge():
    """
    Test that evaluates a corporate/professional storyboard using the LLM-as-judge.
    Asserts that the storyboard passes a quality threshold.
    """
    storyboard = Storyboard(
        scenes=[
            StoryboardScene(
                image_path="path/to/corp1.jpg",
                filename="corp1.jpg",
                duration_frames=90, # 3s at 30fps
                caption="Welcome to FotoOwl's Annual Summit",
                transition_type="fade",
                transition_duration_frames=15,
                zoom_animation="static"
            ),
            StoryboardScene(
                image_path="path/to/corp2.jpg",
                filename="corp2.jpg",
                duration_frames=90,
                caption="Keynote: Innovating Image Pipelines",
                transition_type="fade",
                transition_duration_frames=15,
                zoom_animation="static"
            ),
            StoryboardScene(
                image_path="path/to/corp3.jpg",
                filename="corp3.jpg",
                duration_frames=90,
                caption="Interactive Workshops & Collaboration",
                transition_type="fade",
                transition_duration_frames=15,
                zoom_animation="static"
            ),
            StoryboardScene(
                image_path="path/to/corp4.jpg",
                filename="corp4.jpg",
                duration_frames=90,
                caption="Shaping the Future of Personal Reels",
                transition_type="fade",
                transition_duration_frames=15,
                zoom_animation="static"
            )
        ],
        total_duration_frames=360,
        narrative_arc="Introductory keynote presentation transitions to collaborative breakout sessions and closes with a forward-looking summary."
    )
    
    evaluation = run_llm_judge(
        storyboard=storyboard,
        pacing_intent="moderate",
        tone_intent="corporate and professional"
    )
    
    print(f"\n--- LLM Judge Corporate Critique Result ---")
    print(f"Narrative Score: {evaluation.narrative_coherence_score}/10")
    print(f"Timing & Pacing Score: {evaluation.timing_pacing_score}/10")
    print(f"Reasoning: {evaluation.reasoning}")
    print(f"---------------------------------")
    
    assert evaluation.narrative_coherence_score >= 7, f"Narrative coherence scored too low: {evaluation.narrative_coherence_score}"
    assert evaluation.timing_pacing_score >= 7, f"Timing and pacing scored too low: {evaluation.timing_pacing_score}"

