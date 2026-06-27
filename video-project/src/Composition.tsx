import { AbsoluteFill, interpolate, useCurrentFrame, staticFile, Sequence } from 'remotion';
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
    [startFrame, startFrame + overlap],
    [0, 1],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
  );

  const scale = safeInterpolate(
    frame,
    [startFrame, startFrame + scene.duration_frames],
    [1.0, 1.15],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
  );

  const imgUrl = staticFile("images/" + scene.filename);

  return (
    <AbsoluteFill style={{ opacity }}>
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', position: 'relative', width: '100%', height: '100%', overflow: 'hidden' }}>
        <img src={imgUrl} style={{ position: 'absolute', width: '100%', height: '100%', objectFit: 'cover', filter: 'blur(20px) brightness(0.4)' }} />
        <img src={imgUrl} style={{ position: 'relative', height: '100%', maxWidth: '100%', objectFit: 'contain', transform: `scale(${scale})` }} />
        <div style={{ position: 'absolute', bottom: 0, width: '100%', height: '20%', backgroundColor: 'linear-gradient(0deg, rgba(0,0,0,0.5), transparent)' }} />
        <div style={{ position: 'absolute', bottom: 20, width: '100%', textAlign: 'center', color: 'white', fontSize: 24 }}>{scene.caption}</div>
      </div>
    </AbsoluteFill>
  );
};

export const MainVideo: React.FC = () => {
  let startFrame = 0;
  return (
    <AbsoluteFill>
      {storyboard.scenes.map((scene, index) => {
        const overlap = index === 0 ? 0 : scene.transition_duration_frames;
        return (
          <Sequence from={startFrame} key={index}>
            <Slide scene={scene} startFrame={startFrame} overlap={overlap} />
          </Sequence>
        );
        startFrame += scene.duration_frames - overlap;
      })}
    </AbsoluteFill>
  );
};