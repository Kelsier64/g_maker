# G-Maker - AI Video Generator

G-Maker is an AI-powered automated video generation pipeline. It is designed to transform reference content (such as YouTube videos or raw text) into highly engaging, short-form videos complete with automated narration, synchronized subtitles, and AI-generated visuals.

## Features

- **End-to-End Generation**: From script processing to final video rendering.
- **AI Text-to-Speech (TTS)**: Realistic voiceovers using ElevenLabs.
- **Lip-Synced Speaker Animation**: Generates an animated avatar matching the generated audio.
- **Automated Subtitles**: Transcription via Whisper, with dynamic styling (ASS format) and word-level timing.
- **Visual Generation**: Leverages a local Text-to-Video (T2V) server running CogVideoX for contextual background videos.
- **State Management**: Robust SQLite database backend to track processing states, allowing for easy resumption and monitoring.
- **Modular Pipeline**: Decoupled services for fetching, processing, and generating media.

## Prerequisites

- Python >= 3.12
- [uv](https://github.com/astral-sh/uv) (for fast dependency management)
- FFmpeg installed and available in your system path
- Access to a local T2V API server (running on `localhost:8000`)
- API Keys for OpenAI and ElevenLabs

## Setup & Installation

1. **Clone the repository** and navigate to the root directory.

2. **Install dependencies** using `uv`:
   ```bash
   uv sync
   ```

3. **Configure Environment Variables**:
   Ensure you have a `.env` file in the root directory containing your necessary API keys (OpenAI, ElevenLabs, etc.).

4. **Initialize the Database**:
   ```bash
   uv run python scripts/init_database.py
   ```

## Usage

### Running the Main Pipeline

To start generating a video, run the main application:

```bash
uv run python src/g_maker/main.py
```

### Database Management

You can inspect your video projects and processing states using the included database CLI scripts:

```bash
uv run python scripts/db_manager.py list    # View all projects
uv run python scripts/db_manager.py stats   # View processing statistics
```

## Testing

Run tests directly with Python via `uv`:

```bash
uv run python tests/test.py
uv run python scripts/test_database.py
```
