import { Composition } from 'remotion';
import { MainVideo } from './Composition';
import storyboard from './storyboard.json';

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="my-video"
        component={MainVideo}
        durationInFrames={storyboard.total_duration_frames || 150}
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};
