STYLE_GUIDES = [
    {
        "id": "style_cinematic",
        "theme": "cinematic",
        "content": """Cinematic Video Style Guide:
- Pacing: Slow and emotional, 3.5 to 4.5 seconds (105-135 frames at 30fps) per image.
- Transitions: Smooth Crossfade (duration 0.8s - 1.0s or 24-30 frames).
- Animations: Slow, subtle Ken Burns camera zoom (scale from 1.0 to 1.12 over the slide duration).
- Captions: Small, elegant mixed-case text in a clean font. Centered at the bottom with a semi-transparent dark pill background (padding: 8px 16px, borderRadius: 20px). Low-key visual layout.
- Tone: Sentimental, romantic, emotional, warm tones, high contrast.
- Layout: Fullscreen covered image with object-fit: cover, absolute centering."""
    },
    {
        "id": "style_upbeat",
        "theme": "upbeat",
        "content": """Upbeat and Energetic Video Style Guide:
- Pacing: Fast and energetic, 1.2 to 1.8 seconds (36-54 frames at 30fps) per image.
- Transitions: Fast cuts or snappy Slide/Pop transitions (duration 0.15s - 0.25s or 5-8 frames).
- Animations: Snappy zoom-in or bounce effects (scale from 1.0 to 1.25, or spring bounce on entry).
- Captions: Bold, large, uppercase text. Uses vibrant primary colors or outlines (e.g. bright yellow or white with heavy black text-shadow). Pop-in or scale spring animation for captions.
- Tone: High energy, fun, exciting, colorful, high contrast.
- Layout: Colorful borders, overlapping layers, or full-bleed dynamic scaling."""
    },
    {
        "id": "style_corporate",
        "theme": "corporate",
        "content": """Corporate and Professional Video Style Guide:
- Pacing: Moderate and clean, 2.5 to 3.2 seconds (75-96 frames at 30fps) per image.
- Transitions: Clean Slide-Left/Right or simple quick Dissolve (duration 0.4s - 0.6s or 12-18 frames).
- Animations: Subtle linear panning (translate X or Y from -15px to 15px over the slide duration). No scaling.
- Captions: Minimalist professional text. Left-aligned or boxed in a solid side/bottom banner (dark blue, gray, or white with dark text). Uses clean geometric fonts.
- Tone: Professional, informative, trustworthy, clean, neutral colors.
- Layout: Framed slides with solid colored borders, or split-screens showing titles clearly."""
    }
]

REMOTION_API_SNIPPETS = [
    {
        "id": "api_sequence",
        "component": "Sequence",
        "content": """Remotion Sequence Component:
Use the <Sequence> component to coordinate the timing of elements in your video.
Each slide should be placed in its own Sequence with a calculated 'from' frame and 'durationInFrames'.
Example:
```tsx
import { Sequence } from 'remotion';

export const MyComposition = () => {
  return (
    <div>
      {/* Slide 1 runs from frame 0 for 90 frames */}
      <Sequence from={0} durationInFrames={90}>
        <SlideImage src="img1.jpg" />
      </Sequence>
      {/* Slide 2 runs from frame 90 for 90 frames */}
      <Sequence from={90} durationInFrames={90}>
        <SlideImage src="img2.jpg" />
      </Sequence>
    </div>
  );
};
```"""
    },
    {
        "id": "api_spring_animation",
        "component": "spring",
        "content": """Remotion spring animation function:
Use 'spring' for natural, physics-based animations (like zoom-in pop-up captions or smooth transition effects).
Example:
```tsx
import { spring, useCurrentFrame, useVideoConfig } from 'remotion';

export const ZoomCaption: React.FC<{ text: string }> = ({ text }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  
  // Spring goes from 0 to 1
  const scale = spring({
    frame,
    fps,
    config: {
      damping: 12,   // control bounciness (lower = more bouncy)
      mass: 0.5,      // speed of movement
      stiffness: 100, // tension
    },
  });
  
  return (
    <div style={{ transform: `scale(${scale})`, fontSize: 40, fontWeight: 'bold' }}>
      {text}
    </div>
  );
};
```"""
    },
    {
        "id": "api_interpolate",
        "component": "interpolate",
        "content": """Remotion interpolate function:
Use 'interpolate' to map a linear range (e.g. frame number) to a style range (like scale, opacity, rotation, or position translation).
Excellent for custom Ken Burns effects or fade transitions.
Example:
```tsx
import { interpolate, useCurrentFrame, useVideoConfig } from 'remotion';

export const Slide: React.FC<{ imageSrc: string }> = ({ imageSrc }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  
  // Ken Burns zoom effect: scale from 1.0 to 1.15 over the entire slide duration
  const scale = interpolate(
    frame,
    [0, durationInFrames],
    [1.0, 1.15],
    { extrapolateRight: 'clamp' }
  );
  
  // Fade-in entry: opacity goes from 0 to 1 in the first 15 frames
  const opacity = interpolate(
    frame,
    [0, 15],
    [0, 1],
    { extrapolateRight: 'clamp' }
  );
  
  return (
    <div style={{ opacity, width: '100%', height: '100%', overflow: 'hidden' }}>
      <img
        src={imageSrc}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          transform: `scale(${scale})`,
        }}
      />
    </div>
  );
};
```"""
    },
    {
        "id": "api_static_file",
        "component": "staticFile",
        "content": """Remotion staticFile helper:
Use the 'staticFile' helper to reference images or assets stored in the 'public' directory of the Remotion project.
Do not use relative file imports like '../public/image.jpg'. Use staticFile("image.jpg").
Example:
```tsx
import { staticFile } from 'remotion';

export const MyImage = () => {
  // Points to video-project/public/images/wedding1.jpg
  const imgUrl = staticFile("images/wedding1.jpg");
  return <img src={imgUrl} style={{ width: '100%', height: '100%' }} />;
};
```"""
    },
    {
        "id": "api_crossfade_transition",
        "component": "Transition",
        "content": """Remotion Crossfade Transition Example:
To crossfade between two overlapping sequences, overlap them by N frames, and use interpolate in the overlap region.
Example:
```tsx
import { AbsoluteFill, interpolate, useCurrentFrame } from 'remotion';

export const CrossfadeSlide: React.FC<{
  imageSrc: string;
  duration: number;
  overlap: number; // overlap frames at the start
}> = ({ imageSrc, duration, overlap }) => {
  const frame = useCurrentFrame();
  
  // Fade in at the beginning of this slide's sequence (during the overlap region)
  const opacity = interpolate(
    frame,
    [0, overlap],
    [0, 1],
    { extrapolateRight: 'clamp' }
  );
  
  return (
    <AbsoluteFill style={{ opacity }}>
      <img src={imageSrc} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
    </AbsoluteFill>
  );
};
```"""
    }
]
