import cv2
import numpy as np
import librosa
import subprocess
import tempfile
import os



def create_speaker_video(mp3_path: str, closed_mouth_jpg: str, open_mouth_jpg: str,
                                 output_path: str, fps: int = 16, sensitivity: float = 0.4) -> None:
    """
    Advanced version with smoothing and better mouth movement detection using ffmpeg.
    
    Args:
        mp3_path: Path to the MP3 audio file
        closed_mouth_jpg: Path to closed mouth image
        open_mouth_jpg: Path to open mouth image
        output_path: Path for output video file
        fps: Frames per second for output video
        sensitivity: Mouth opening sensitivity (0.0 - 1.0)
    """
    # Load and analyze audio
    audio, sr = librosa.load(mp3_path, sr=None)
    duration = len(audio) / sr
    total_frames = int(duration * fps)
    
    # Use onset detection for better speech timing
    onset_frames = librosa.onset.onset_detect(y=audio, sr=sr, units='time')
    
    # Calculate RMS with smoothing
    frame_length = int(sr / fps)
    rms_values = []
    
    for i in range(total_frames):
        start_sample = int(i * frame_length)
        end_sample = min(start_sample + frame_length, len(audio))
        
        if start_sample < len(audio):
            frame = audio[start_sample:end_sample]
            rms = np.sqrt(np.mean(frame ** 2)) if len(frame) > 0 else 0
        else:
            rms = 0
        rms_values.append(rms)
    
    # Smooth RMS values
    rms_values = np.array(rms_values)
    window_size = max(1, fps // 10)  # 0.1 second smoothing
    rms_smooth = np.convolve(rms_values, np.ones(window_size)/window_size, mode='same')
    
    # Dynamic threshold based on sensitivity
    threshold = np.percentile(rms_smooth[rms_smooth > 0], (1 - sensitivity) * 100)
    
    # Load and prepare images
    closed_img = cv2.imread(closed_mouth_jpg)
    open_img = cv2.imread(open_mouth_jpg)
    
    if closed_img is None or open_img is None:
        raise ValueError("Could not load mouth images")
    
    height, width = closed_img.shape[:2]
    open_img = cv2.resize(open_img, (width, height))
    
    # Create temporary directory for frames
    with tempfile.TemporaryDirectory() as temp_dir:
        # Generate frames with mouth state
        for i in range(total_frames):
            # Check if mouth should be open
            is_speaking = rms_smooth[i] > threshold
            
            if is_speaking:
                frame = open_img.copy()
            else:
                frame = closed_img.copy()
            
            frame_path = os.path.join(temp_dir, f"frame_{i:06d}.png")
            cv2.imwrite(frame_path, frame)
        
        # Use ffmpeg to create video with high quality settings
        frame_pattern = os.path.join(temp_dir, "frame_%06d.png")
        
        ffmpeg_cmd = [
            'ffmpeg', '-y',
            '-framerate', str(fps),
            '-i', frame_pattern,
            '-i', mp3_path,
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-c:a', 'aac',
            '-b:a', '128k',
            '-pix_fmt', 'yuv420p',
            '-shortest',
            output_path
        ]
        
        subprocess.run(ffmpeg_cmd, check=True)

# Example usage
if __name__ == "__main__":

    create_speaker_video(
        mp3_path="sound.mp3",
        closed_mouth_jpg="close.jpg",
        open_mouth_jpg="open.jpg", 
        output_path="speaker_video.mp4",
        sensitivity=0.6
    )
    
