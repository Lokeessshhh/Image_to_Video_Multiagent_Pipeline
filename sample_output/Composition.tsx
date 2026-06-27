import React from 'react';
import {
	AbsoluteFill,
	Sequence,
	interpolate,
	useCurrentFrame,
	staticFile,
} from 'remotion';
import storyboard from './storyboard.json';

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

const computeStartFrames = (scenes: StoryboardScene[]): number[] => {
	const starts: number[] = [];
	let currentStart = 0;
	for (let i = 0; i < scenes.length; i++) {
		starts.push(currentStart);
		const prevTransition =
			i > 0 ? scenes[i - 1].transition_duration_frames : 0;
		currentStart = currentStart + scenes[i].duration_frames - prevTransition;
	}
	return starts;
};

const Slide: React.FC<{ scene: StoryboardScene }> = ({ scene }) => {
	const {
		filename,
		caption,
		duration_frames,
		transition_type,
		transition_duration_frames,
		zoom_animation,
	} = scene;

	const frame = useCurrentFrame();

	// Opacity handling for crossfade transitions
	let opacity = 1;
	if (transition_type === 'crossfade' && transition_duration_frames > 0) {
		const fadeIn = interpolate(
			frame,
			[0, transition_duration_frames],
			[0, 1],
			{ extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
		);
		const fadeOut = interpolate(
			frame,
			[duration_frames - transition_duration_frames, duration_frames],
			[1, 0],
			{ extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
		);
		opacity = Math.min(fadeIn, fadeOut);
	}

	// Simple zoom_in animation (Ken Burns)
	const scale =
		zoom_animation === 'zoom_in'
			? interpolate(
					frame,
					[0, duration_frames],
					[1, 1.15],
					{ extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
			  )
			: 1;

	const imgSrc = staticFile(`images/${filename}`);

	return (
		<AbsoluteFill style={{ opacity }}>
			<div
				style={{
					display: 'flex',
					justifyContent: 'center',
					alignItems: 'center',
					position: 'relative',
					width: '100%',
					height: '100%',
					overflow: 'hidden',
				}}
			>
				{/* Background blurred image */}
				<img
					src={imgSrc}
					alt=""
					style={{
						position: 'absolute',
						width: '100%',
						height: '100%',
						objectFit: 'cover',
						filter: 'blur(20px) brightness(0.4)',
						transform: `scale(${scale})`,
					}}
				/>
				{/* Foreground clear image */}
				<img
					src={imgSrc}
					alt={caption}
					style={{
						position: 'relative',
						maxWidth: '100%',
						height: '100%',
						objectFit: 'contain',
						transform: `scale(${scale})`,
					}}
				/>
				{/* Gradient overlay for caption readability */}
				<div
					style={{
						position: 'absolute',
						bottom: 0,
						left: 0,
						right: 0,
						height: '30%',
						background:
							'linear-gradient(to top, rgba(0,0,0,0.7), transparent)',
						pointerEvents: 'none',
					}}
				/>
				{/* Caption */}
				<div
					style={{
						position: 'absolute',
						bottom: 20,
						left: 0,
						right: 0,
						textAlign: 'center',
						color: '#fff',
						fontSize: 48,
						fontWeight: 400,
						padding: '0 20px',
						textShadow: '0 2px 4px rgba(0,0,0,0.6)',
					}}
				>
					{caption}
				</div>
			</div>
		</AbsoluteFill>
	);
};

export const MainVideo: React.FC = () => {
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
					<Slide scene={scene} />
				</Sequence>
			))}
		</AbsoluteFill>
	);
};