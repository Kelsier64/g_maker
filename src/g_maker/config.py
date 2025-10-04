from pathlib import Path

VIDEO_FPS = 60
G_VIDEO_FPS = 16
VOICE_ID = "MFZUKuGQUsGJPQjTS4wC"
STT_MODE = "word"  # segment
AUTO_UPLOAD = False  # Enable automatic YouTube upload after video completion
COMFY_ADDRESS = "127.0.0.1:8188"


CURRENT_DIR = Path(__file__).resolve().parent
BASE_DIR = CURRENT_DIR.parent.parent

PATHS = {
    "GENERATED_VIDEOS_DIR": BASE_DIR / "generated_videos",
    "FINAL_VIDEOS_DIR": BASE_DIR / "output",
    "TEMP_DIR": BASE_DIR / "temp",
    "AUDIO_PATH": BASE_DIR / "temp" / "audio.mp3",
    "BASE_VIDEO": BASE_DIR / "temp" / "base_video.mp4",
    "COMBINED_VIDEO": BASE_DIR / "temp" / "combined_video.mp4",
    "BLURRED_VIDEO": BASE_DIR / "temp" / "blurred_video.mp4",
    "REF_AUDIO": BASE_DIR / "temp" / "ref_audio.mp3",
    "SRT": BASE_DIR / "temp" / "script_timestamps.srt",
    "ASS": BASE_DIR / "temp" / "subtitles.ass",
    "CLOSE_JPG": BASE_DIR / "static" / "close.jpg",
    "OPEN_JPG": BASE_DIR / "static" / "open.jpg",
    "CONFIG": BASE_DIR / "config",
    "WORKFLOW_PATH": BASE_DIR / "static" / "kj720p.json",
}
