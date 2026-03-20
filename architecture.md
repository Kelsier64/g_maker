# G-Maker Architecture & System Design

G-Maker is an AI-powered automated video generation pipeline. Its modular architecture handles everything from content ingestion to the final rendered video clip with subtitles, AI voiceovers, and generated visual segments.

## 1. High-Level Architecture Overview

The system is designed with explicit boundaries between data acquisition, AI processing, file manipulation, and database logging. 

- **State Management**: A SQLite database (`videos.db`) tracks the lifecycle of every video project.
- **Service Integration**: External APIs (OpenAI, ElevenLabs) are abstracted behind unified client interfaces.
- **Processing Layer**: Heavy media manipulation (FFmpeg, OpenCV, subtitle generation) occurs in isolated modules.
- **Content Pipeline**: The `main.py` orchestrator runs videos through a defined 7-step production pipeline.

## 2. Directory Structure

```text
g_maker/
├── src/g_maker/
│   ├── config.py           # Central configuration (Paths, API settings, Output FPS)
│   ├── main.py             # Main entry point and orchestration pipeline
│   ├── video_manager.py    # Database wrapper for state and metadata logging
│   ├── models/             # Pydantic models for data validation and API parsing
│   ├── input/              # Content acquisition (e.g., youtube downloader)
│   ├── processing/         # Media manipulation (Video, Audio, Subtitles, OpenCV)
│   ├── services/           # External API clients (OpenAI, ElevenLabs, Local T2V)
│   └── utils/              # Shared utilities (Terminal UI, Spinners)
├── scripts/                # Utility scripts for DB initialization and management
├── tests/                  # Simple python test scripts
├── static/                 # Static assets (avatar open/close mouth images)
├── temp/                   # Temporary processing workspace (cleared after runs)
└── output/                 # Final rendered videos
```

## 3. The 7-Step Video Production Pipeline

The core application in `src/g_maker/main.py` orchestrates the following sequence. Every step is logged as "started", "completed", or "failed" via `video_manager.py`.

1. **Audio Generation**: Text-to-speech using ElevenLabs API. Large transcripts are chunked to fit within API constraints.
2. **Speaker Video Generation**: `make_speaker.py` uses OpenCV and static assets (`static/close.jpg`, `static/open.jpg`) to generate animated lip-synced avatars matching the audio waveform.
3. **Subtitle Generation**: Audio is transcribed via OpenAI Whisper (word-level or segment-level depending on `STT_MODE`). The output is converted from SRT to Advanced SubStation Alpha (`.ass`) formatting for styled text rendering (popups, colors).
4. **Prompt Generation**: AI (Azure/OpenAI) analyzes the script and timestamps to generate visual prompt concepts that match the audio context.
5. **Video Generation**: Text-to-Video API calls are dispatched to a local server running CogVideoX (`localhost:8000`) based on the generated visual prompts.
6. **Video Assembly**: `video_processing.py` uses FFmpeg wrappers to combine generated video segments, apply background blur effects (if necessary), and synchronize audio.
7. **Final Output**: The pipeline burns the styled ASS subtitles onto the assembled video and saves the final product to the `output/` directory at `VIDEO_FPS` (e.g., 60 FPS).

## 4. Key Design Patterns

### Database Tracking
All operations are wrapped with the `video_manager`. The pipeline relies heavily on this tracking to recover from failures and provide transparency.
```python
video_id = video_manager.create_video_project(title, script)
video_manager.start_processing(video_id, "step_name", "description")
# logic...
video_manager.complete_processing_step(video_id, "step_name", "success")
```

### Error Handling
Errors never fail silently. They are caught, logged to the `videos.db` state machine, reported via the `terminal` UI wrapper, and raised to stop the pipeline gracefully.

### UI / CLI Output
Raw `print()` statements are avoided. Instead, `utils/terminal.py` is used to provide a consistent visual representation of the processing state (SUCCESS, ERROR, PROCESSING, WARNING) alongside multi-threaded loading spinners.
