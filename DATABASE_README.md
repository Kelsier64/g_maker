# G-Maker Video Database Documentation

G-Maker now includes a comprehensive SQLite database system to manage output videos, track processing steps, and store metadata.

## Features

- **Video Records**: Store video metadata including title, script, file path, duration, resolution, etc.
- **Processing Logs**: Track each step of video generation with timestamps and status
- **Prompts Storage**: Store AI prompts used for video generation
- **Error Handling**: Track failed processing steps and error messages
- **Statistics**: Get insights into your video database

## Database Schema

### Videos Table
- `id`: Primary key
- `title`: Video title
- `script`: Original script text
- `file_path`: Path to the final video file
- `file_size`: File size in bytes
- `duration`: Video duration in seconds
- `fps`: Frames per second
- `resolution`: Video resolution (e.g., "1920x1080")
- `status`: Processing status ("created", "processing", "completed", "failed")
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp
- `metadata`: JSON metadata (additional video properties)

### Prompts Table
- `id`: Primary key
- `video_id`: Foreign key to videos table
- `prompt`: AI prompt text
- `start_time`: When prompt starts in video
- `duration`: Prompt duration
- `created_at`: Creation timestamp

### Processing Logs Table
- `id`: Primary key
- `video_id`: Foreign key to videos table
- `step`: Processing step name
- `status`: Step status ("started", "completed", "failed")
- `message`: Optional message or error description
- `timestamp`: Log timestamp

## Usage

### In the Main Application

The database is automatically integrated into the video pipeline. When you create videos:

1. A video record is created at the start
2. Each processing step is logged
3. Prompts are stored
4. Final video metadata is extracted and stored
5. Error states are tracked

### Menu Options

The main application menu now includes database management options:

- **View video database**: List recent videos with status
- **Show database stats**: Display database statistics
- **View video details**: Show detailed info for a specific video
- **Delete video**: Remove a video and its files

### Command Line Manager

Use the database manager script for advanced operations:

```bash
# List all videos
python scripts/db_manager.py list

# List only completed videos
python scripts/db_manager.py list --status completed

# Show details for video ID 5
python scripts/db_manager.py show 5

# Show database statistics
python scripts/db_manager.py stats

# Delete video ID 3
python scripts/db_manager.py delete 3

# Delete video without confirmation
python scripts/db_manager.py delete 3 --force

# Remove all failed videos
python scripts/db_manager.py cleanup

# Export database to JSON
python scripts/db_manager.py export my_videos.json
```

## Python API

You can also interact with the database programmatically:

```python
from g_maker.video_manager import video_manager
from g_maker.database import db

# Create a video project
video_id = video_manager.create_video_project(
    title="My Video",
    script="Hello world script"
)

# Get video info
video = video_manager.get_video(video_id)
print(f"Video: {video.title}, Status: {video.status}")

# List videos
videos = video_manager.list_videos(status="completed", limit=10)

# Log processing steps
video_manager.start_processing(video_id, "encoding", "Starting video encoding")
video_manager.complete_processing_step(video_id, "encoding", "Encoding completed")

# Set video file and extract metadata
video_manager.set_video_file(video_id, "/path/to/video.mp4")

# Get processing logs
logs = video_manager.get_processing_logs(video_id)
for log in logs:
    print(f"{log.timestamp}: {log.step} - {log.status}")

# Get database statistics
stats = db.get_video_stats()
print(f"Total videos: {stats['total_videos']}")
```

## Database Location

The SQLite database is created as `videos.db` in the project root directory.

## Benefits

1. **Tracking**: Keep track of all generated videos and their processing history
2. **Debugging**: Easy identification of failed videos and error messages
3. **Analytics**: Understand your video generation patterns and success rates
4. **Management**: Easy cleanup of failed attempts and old videos
5. **Backup**: Export database for backup or migration
6. **Metadata**: Automatic extraction and storage of video properties

## Migration

If you have existing videos, they won't automatically appear in the database. The database will start tracking videos from the first run after the update. You can manually add existing videos using the Python API if needed.
