# G-Maker Agent Instructions (AGENTS.md)

Welcome to the G-Maker AI Video Generator project. You are an autonomous coding agent operating in this repository. Please strictly follow these guidelines when analyzing, modifying, or creating code here.

## 1. Project Overview & Architecture
G-Maker is an AI-powered video generation pipeline that transforms reference content into short-form videos with automated narration, subtitles, and visuals.
It relies on a modular architecture:
- `src/g_maker/services/`: External API clients (OpenAI, ElevenLabs, local T2V server).
- `src/g_maker/processing/`: Video manipulation (FFmpeg wrappers, subtitle formatting, mouth animation).
- `src/g_maker/input/`: Content acquisition (YouTube downloader).
- `src/g_maker/models/`: Pydantic models for data validation.
- `src/g_maker/video_manager.py`: SQLite wrapper for tracking processing states.
- `src/g_maker/utils/`: Shared utilities like the terminal UI reporter.

## 2. Setup, Build, and Execution Commands

This project uses `uv` for dependency management. Ensure `uv` is used for all executions.

### Running the Application
To run the main application pipeline:
```bash
uv run python src/g_maker/main.py
```

### Running Tests
The project tests are simple python scripts located in the `tests/` and `scripts/` directories.
To run a single test, execute it directly with python via uv:
```bash
uv run python tests/test.py
uv run python tests/ass_test.py
uv run python scripts/test_database.py
```

### Database Management Tools
Use the provided CLI scripts to interact with the database:
```bash
uv run python scripts/init_database.py     # Initialize database
uv run python scripts/db_manager.py list   # List projects
uv run python scripts/db_manager.py stats  # View DB stats
```

## 3. Code Style and Development Guidelines

### Imports and Formatting
- Keep imports organized. Prefer absolute imports from the `g_maker` namespace (e.g., `from g_maker.services import t2v_api_client`).
- Rely on standard python features (>= 3.12).
- Ensure variables and functions use `snake_case`. Classes should use `PascalCase`.

### Database Integration Pattern (Critical)
All video processing operations MUST use the `video_manager` to log state and metadata.
```python
from g_maker.video_manager import video_manager

# Create video project
video_id = video_manager.create_video_project(title, script)

# Wrap processing steps
video_manager.start_processing(video_id, "step_name", "description")
# ... perform work ...
video_manager.complete_processing_step(video_id, "step_name", "success_message")
```

### Error Handling Pattern
Always use try-except blocks combined with database logging for critical steps. Never let a pipeline step fail silently without updating the database state.
```python
try:
    # Attempt processing step
    video_manager.complete_processing_step(video_id, "step_name", "Success")
except Exception as e:
    video_manager.fail_processing_step(video_id, "step_name", str(e))
    # Optionally log to terminal
    terminal.print_status(f"Error: {e}", "ERROR")
    raise
```

### User Interface & Terminal Output
Do not use raw `print()` statements for pipeline status. Instead, use `utils/terminal.py`:
```python
from g_maker.utils import terminal

terminal.print_separator("Section Title")
terminal.print_status("Processing started", "PROCESSING")
terminal.print_status("Task finished", "SUCCESS")
terminal.print_status("Something went wrong", "ERROR")

spinner = terminal.SpinnerThread("Loading...")
spinner.start()
# do work
spinner.stop()
```

### Configuration and File Paths
- Never hardcode file paths. All paths (temp directories, static assets like `close.jpg`, output directories) are managed centrally.
- Import `PATHS` from `g_maker.config` (e.g., `from g_maker.config import PATHS`).
- Use the central configuration for video settings like `VIDEO_FPS`, `STT_MODE`, and `G_VIDEO_FPS`.

### Type Hints and Data Validation
- Use type hints (`int`, `str`, `list`, `dict`) on all function signatures where practical.
- Use `Pydantic` models (from `src/g_maker/models.py`) for structured data validation, especially for API responses and script generation.

### Modularity and Boundaries
- Keep external API calls strictly in `services/`.
- Keep FFmpeg, OpenCV, and other file manipulation logic strictly in `processing/`.
- Do not mix database logging directly into low-level processing functions; keep the DB state management orchestrated at the high-level (like in `main.py`).

## 4. AI Service Integration Points
- **Azure OpenAI / OpenAI**: Main generation, transcription.
- **ElevenLabs**: TTS audio generation.
- **Local T2V Server**: Requires local server at `localhost:8000` for video generation (CogVideoX model). Check health via `t2v_api_client.check_health()`.

## 5. Temporary Files and Memory Management
- Audio files might exceed API limits (like Whisper's 24MB limit) and must be chunked.
- Ensure temporary files in `temp/` are cleaned up or overwritten gracefully during processing cycles. Use `PATHS["TEMP_DIR"]`.
