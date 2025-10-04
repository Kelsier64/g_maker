# G-Maker AI Video Generator - Copilot Instructions

## Project Overview
G-Maker is an AI-powered video generation pipeline that transforms YouTube reference content into short-form videos with automated narration, subtitles, and visual generation. It uses a modular architecture with distinct service boundaries for AI APIs, video processing, and database management.

## Architecture & Core Pipeline

### 7-Step Video Production Pipeline (`src/g_maker/main.py`)
1. **Audio Generation**: Text-to-speech via ElevenLabs API
2. **Speaker Video**: Animated mouth movements synced to audio (`make_speaker.py`)
3. **Subtitle Generation**: Whisper transcription → SRT → ASS with custom styling
4. **Prompt Generation**: AI generates visual prompts from script timestamps
5. **Video Generation**: Text-to-video API calls via local server (`t2v_api_client.py`)
6. **Video Assembly**: Combines segments, applies blur effects
7. **Final Output**: Burns subtitles and saves to output directory

### Service Boundaries
- **`services/`**: External API clients (OpenAI, ElevenLabs, T2V server)
- **`processing/`**: Video manipulation (FFmpeg wrappers, subtitle processing)
- **`input/`**: Content acquisition (YouTube downloader)
- **Database layer**: SQLite with full processing logs and metadata

## Critical Development Patterns

### Database Integration
All video operations use `video_manager.py` which wraps database operations:
```python
# Always create video project first, returns video_id for tracking
video_id = video_manager.create_video_project(title, script)
video_manager.start_processing(video_id, "step_name", "description")
video_manager.complete_processing_step(video_id, "step_name", "success_message")
```

### Error Handling Pattern
Use try-except with database logging:
```python
try:
    # processing step
    video_manager.complete_processing_step(video_id, step, message)
except Exception as e:
    video_manager.fail_processing_step(video_id, step, str(e))
    raise
```

### Configuration Management
Central config in `config.py` with directory paths and processing settings:
- `PATHS`: All file paths (temp/, output/, static/)
- `STT_MODE`: "word" vs "segment" for subtitle timing
- `VIDEO_FPS`: Output framerate (60 for final, 16 for generated segments)

### Terminal UI Conventions
Use `utils/terminal.py` for consistent status reporting:
```python
terminal.print_separator("Section Title")
terminal.print_status("Message", "PROCESSING|SUCCESS|ERROR|WARNING")
spinner = terminal.SpinnerThread("Loading..."); spinner.start(); spinner.stop()
```

## Development Workflows

### Running with UV
Project uses `uv` for dependency management:
```bash
uv run python src/g_maker/main.py  # Main application
uv run python scripts/db_manager.py list  # Database CLI tools
```

### Testing Database Features
```bash
uv run python scripts/init_database.py  # Initialize database
uv run python scripts/test_database.py  # Test functionality
uv run python scripts/db_manager.py stats  # View database stats
```

### Debugging Video Pipeline
- Check `videos.db` for processing logs and error states
- Temp files preserved in `./temp/` for debugging
- Use `video_manager.print_video_info(video_id)` for detailed logs

## AI Service Integration Points

### Multi-Provider AI Pattern
Different providers for different tasks:
- **Azure OpenAI**: Main GPT requests, Whisper transcription
- **OpenAI**: Backup/alternative model access
- **ElevenLabs**: Text-to-speech with voice cloning
- **Local T2V Server**: Video generation (CogVideoX model)

### API Client Structure (`services/ai_api_clients.py`)
Standardized request/response pattern with Pydantic models:
```python
def gpt_request(messages, response_model=None):
    # Handles both text and structured responses
    # Uses response_model for Pydantic parsing when provided
```

### Local T2V Server Dependency
Critical: Requires local server at `localhost:8000` for video generation
- Health check: `t2v_api_client.check_health()`
- Queue management and task monitoring built-in
- Graceful failure handling when server unavailable

## File Organization Conventions

### Processing Steps Are Modular
Each processing module in `processing/` handles one concern:
- `make_speaker.py`: Lip-sync animation using OpenCV
- `srt_processing.py`: Subtitle format conversion and styling
- `video_processing.py`: FFmpeg operations (combine, blur, burn subtitles)

### Static Assets Pattern
Mouth animation images in `static/`: `close.jpg`, `open.jpg`
Referenced via `PATHS["CLOSE_JPG"]`, `PATHS["OPEN_JPG"]`

### Script Management
YouTube content → AI cleaning → script generation → video production
Each step logged in database with full provenance tracking

## Key Technical Details

### Subtitle Styling System
Custom ASS subtitle styling with effects:
```python
style = {"fontname": "DejaVu Sans", "primarycolor": Color(255,255,255), ...}
srt_processing.srt_to_ass(srt_path, style_dict=style, effects=["popup", "random_colors"])
```

### Video Timing Precision
STT modes affect timing granularity:
- "segment": Sentence-level timing for natural cuts
- "word": Word-level timing for precise synchronization

### Memory Management
Large audio files automatically chunked for Whisper API (24MB limit)
Temporary files cleaned up after each video generation cycle
