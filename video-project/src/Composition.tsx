import { AbsoluteFill, Sequence, interpolate, useCurrentFrame, staticFile } from 'remotion';
import storyboard from './storyboard.json';

const safeInterpolate = (value: number, inputRange: number[], outputRange: number[], options?: { extrapolateLeft?: 'clamp' | 'extend'; extrapolateRight?: 'clamp' | 'extend' }) => {
  if (inputRange[0] === inputRange[1]) return outputRange[0];
  return interpolate(value, inputRange, outputRange, options);
};

interface StoryboardScene {
  image_path: string;
  filename: string;
  duration_frames: number;
  caption: string;
  transition_type: string;
  transition_duration_frames: number;
  zoom_animation: string;
}

interface Storyboard {
  scenes: StoryboardScene[];
  total_duration_frames: number;
  narrative_arc: string;
}

const Slide: React.FC<{ scene: StoryboardScene, startFrame: number, overlap: number }> = ({ scene, startFrame, overlap }) => {
  const frame = useCurrentFrame();

  const opacity = safeInterpolate(
    frame,
    [0, overlap],
    [0, 1],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
  );

  const scale = safeInterpolate(
    frame,
    [0, scene.duration_frames],
    [1.0, 1.15],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
  );

  const imgUrl = staticFile("images/" + scene.filename);

  return (
    <AbsoluteFill style={{ opacity }}>
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', position: 'relative', width: '100%', height: '100%', overflow: 'hidden' }}>
        <img src={imgUrl} style={{ position: 'absolute', width: '100%', height: '100%', objectFit: 'cover', filter: 'blur(20px) brightness(0.4)' }} />
        <img src={imgUrl} style={{ position: 'relative', height: '100%', maxWidth: '100%', objectFit: 'contain', transform: `scale(${scale})` }} />
        <div style={{ position: 'absolute', bottom: 0, width: '100%', height: '20%', backgroundColor: 'linear-gradient(to bottom, rgba(0,0,0,0), rgba(0,0,0,0.5))' }} />
        <div style={{ position: 'absolute', bottom: '10%', left: '10%', fontSize: '24px', color: 'white' }}>{scene.caption}</div>
      </div>
    </AbsoluteFill>
  );
};

export const MainVideo: React.FC = () => {
  const startFrames = storyboard.scenes.reduce((acc: number[], scene: StoryboardScene, index: number) => {
    if (index === 0) {
      acc.push(0);
    } else {
      const previousScene = storyboard.scenes[index - 1];
      acc.push(acc[index - 1] + previousScene.duration_frames - previousScene.transition_duration_frames);
    }
    return acc;
  }, []);

  return (
    <div>
      {storyboard.scenes.map((scene: StoryboardScene, index: number) => (
        <Sequence from={startFrames[index]} durationInFrames={scene.duration_frames} key={index}>
          <Slide scene={scene} startFrame={startFrames[index]} overlap={scene.transition_duration_frames} />
        </Sequence>
      ))}
    </div>
  );
};