import React, { FC } from 'react';
import {
	AbsoluteFill,
	Sequence,
	interpolate,
	useCurrentFrame,
	staticFile,
} from 'remotion';
import storyboard from './storyboard.json';

type StoryboardScene = {
	image_path: string;
	filename: string;
	duration_frames: number;
	caption: string;
	transition_type: string;
	transition_duration_frames: number;
	zoom_animation: string;
};

type Storyboard = {
	scenes: StoryboardScene[];
	total_duration_frames: number;
	narrative_arc: string;
};

const safeInterpolate = (
	value: number,
	inputRange: number[],
	outputRange: number[],
	options?: {
		extrapolateLeft?: 'clamp' | 'extend';
		extrapolateRight?: 'clamp' | 'extend';
	}
) => {
	if (inputRange[0] === inputRange[1]) {
		return outputRange[0];
	}
	return interpolate(value, inputRange, outputRange, options);
};

const computeStartFrames = (scenes: StoryboardScene[]): number[] => {
	return scenes.reduce<number[]>((acc, scene, idx) => {
		if (idx === 0) {
			acc.push(0);
		} else {
			const prev = scenes[idx - 1];
			const prevStart = acc[idx - 1];
			const start = prevStart + prev.duration_frames - prev.transition_duration_frames;
			acc.push(start);
		}
		return acc;
	}, []);
};

const Slide: FC<{
	scene: StoryboardScene;
	isLast: boolean;
}> = ({ scene, isLast }) => {
	const frame = useCurrentFrame();
	const {
		filename,
		caption,
		duration_frames,
		transition_duration_frames,
		zoom_animation,
	} = scene;

	// Opacity handling for crossfade
	let opacity = 1;
	if (frame < transition_duration_frames) {
		opacity = safeInterpolate(
			frame,
			[0, transition_duration_frames],
			[0, 1],
			{ extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
		);
	} else if (!isLast && frame > duration_frames - transition_duration_frames) {
		opacity = safeInterpolate(
			frame,
			[duration_frames - transition_duration_frames, duration_frames],
			[1, 0],
			{ extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
		);
	}

	// Zoom animation
	const scale =
		zoom_animation === 'zoom_in'
			? safeInterpolate(
					frame,
					[0, duration_frames],
					[1, 1.15],
					{ extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
			  )
			: 1;

	const imgSrc = staticFile('images/' + filename);

	const containerStyle: React.CSSProperties = {
		display: 'flex',
		justifyContent: 'center',
		alignItems: 'center',
		position: 'relative',
		width: '100%',
		height: '100%',
		overflow: 'hidden',
	};

	const backgroundStyle: React.CSSProperties = {
		position: 'absolute',
		width: '100%',
		height: '100%',
		objectFit: 'cover',
		filter: 'blur(20px) brightness(0.4)',
	};

	const foregroundStyle: React.CSSProperties = {
		position: 'relative',
		height: '100%',
		maxWidth: '100%',
		objectFit: 'contain',
		transform: `scale(${scale})`,
	};

	const captionStyle: React.CSSProperties = {
		position: 'absolute',
		bottom: '80px',
		left: 0,
		right: 0,
		textAlign: 'center',
		color: 'white',
		fontSize: '32px',
		fontFamily: 'sans-serif',
		textShadow: '0px 2px 8px rgba(0,0,0,0.8)',
		padding: '0 40px',
		zIndex: 10,
	};

	const gradientStyle: React.CSSProperties = {
		position: 'absolute',
		bottom: 0,
		left: 0,
		right: 0,
		height: '30%',
		background: 'linear-gradient(to top, rgba(0,0,0,0.8), transparent)',
		pointerEvents: 'none',
	};

	return (
		<AbsoluteFill style={{ opacity }}>
			<div style={containerStyle}>
				<img src={imgSrc} alt="" style={backgroundStyle} />
				<img src={imgSrc} alt="" style={foregroundStyle} />
				<div style={gradientStyle} />
				<div style={captionStyle}>{caption}</div>
			</div>
		</AbsoluteFill>
	);
};

export const MainVideo: FC = () => {
	const scenes = (storyboard as Storyboard).scenes;
	const startFrames = computeStartFrames(scenes);

	return (
		<AbsoluteFill>
			{scenes.map((scene, idx) => (
				<Sequence
					key={idx}
					from={startFrames[idx]}
					durationInFrames={scene.duration_frames}
				>
					<Slide scene={scene} isLast={idx === scenes.length - 1} />
				</Sequence>
			))}
		</AbsoluteFill>
	);
};