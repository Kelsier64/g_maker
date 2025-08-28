import os
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
import cv2

from g_maker.database import db
from g_maker.models import VideoRecord, VideoPrompt, ProcessingLog, PromptList
from g_maker.utils import terminal

class VideoManager:
    """High-level manager for video operations with database integration."""
    
    def __init__(self):
        self.db = db
    
    def create_video_project(self, title: str, script: str, prompts: PromptList = None) -> int:
        """Create a new video project and return its ID."""
        terminal.print_status(f"Creating video project: {title}", "PROCESSING")
        
        # Create video record
        video_id = self.db.create_video_record(title=title, script=script)
        
        # Add prompts if provided
        if prompts:
            for prompt in prompts.prompts:
                self.db.add_prompt(
                    video_id=video_id,
                    prompt=prompt.prompt,
                    start_time=prompt.start_time,
                    duration=prompt.duration
                )
        
        # Log project creation
        self.db.log_processing_step(video_id, "project_created", "completed", f"Project '{title}' created")
        
        terminal.print_status(f"Video project created with ID: {video_id}", "SUCCESS")
        return video_id
    
    def start_processing(self, video_id: int, step: str, message: str = None):
        """Mark the start of a processing step."""
        self.db.log_processing_step(video_id, step, "started", message)
        self.db.update_video_info(video_id, status="processing")
    
    def complete_processing_step(self, video_id: int, step: str, message: str = None):
        """Mark the completion of a processing step."""
        self.db.log_processing_step(video_id, step, "completed", message)
    
    def fail_processing_step(self, video_id: int, step: str, error_message: str):
        """Mark the failure of a processing step."""
        self.db.log_processing_step(video_id, step, "failed", error_message)
        self.db.update_video_info(video_id, status="failed")
    
    def set_video_file(self, video_id: int, file_path: str):
        """Set the file path for a video and extract metadata."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Video file not found: {file_path}")
        
        # Get file size
        file_size = os.path.getsize(file_path)
        
        # Extract video metadata using OpenCV
        metadata = self._extract_video_metadata(file_path)
        
        # Update database
        self.db.update_video_info(
            video_id=video_id,
            file_path=file_path,
            file_size=file_size,
            duration=metadata.get('duration'),
            fps=metadata.get('fps'),
            resolution=metadata.get('resolution'),
            status="completed",
            metadata=metadata
        )
        
        terminal.print_status(f"Video file registered: {os.path.basename(file_path)}", "SUCCESS")
    
    def _extract_video_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata from video file using OpenCV."""
        try:
            cap = cv2.VideoCapture(file_path)
            
            if not cap.isOpened():
                return {}
            
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            duration = frame_count / fps if fps > 0 else 0
            resolution = f"{width}x{height}"
            
            cap.release()
            
            return {
                'duration': duration,
                'fps': int(fps),
                'resolution': resolution,
                'width': width,
                'height': height,
                'frame_count': int(frame_count)
            }
        except Exception as e:
            terminal.print_status(f"Warning: Could not extract video metadata: {e}", "WARNING")
            return {}
    
    def get_video(self, video_id: int) -> Optional[VideoRecord]:
        """Get a video record."""
        data = self.db.get_video(video_id)
        if data:
            # Parse metadata if it exists
            if data['metadata']:
                try:
                    data['metadata'] = json.loads(data['metadata']) if isinstance(data['metadata'], str) else data['metadata']
                except json.JSONDecodeError:
                    data['metadata'] = {}
            return VideoRecord(**data)
        return None
    
    def list_videos(self, status: str = None, limit: int = None) -> List[VideoRecord]:
        """List videos with optional filtering."""
        videos_data = self.db.get_videos(status=status, limit=limit)
        videos = []
        
        for data in videos_data:
            # Parse metadata if it exists
            if data['metadata']:
                try:
                    data['metadata'] = json.loads(data['metadata']) if isinstance(data['metadata'], str) else data['metadata']
                except json.JSONDecodeError:
                    data['metadata'] = {}
            videos.append(VideoRecord(**data))
        
        return videos
    
    def get_video_prompts(self, video_id: int) -> List[VideoPrompt]:
        """Get prompts for a video."""
        prompts_data = self.db.get_video_prompts(video_id)
        return [VideoPrompt(**data) for data in prompts_data]
    
    def get_processing_logs(self, video_id: int) -> List[ProcessingLog]:
        """Get processing logs for a video."""
        logs_data = self.db.get_processing_logs(video_id)
        return [ProcessingLog(**data) for data in logs_data]
    
    def delete_video(self, video_id: int) -> bool:
        """Delete a video and its files."""
        video = self.get_video(video_id)
        if not video:
            return False
        
        success = self.db.delete_video(video_id)
        if success:
            terminal.print_status(f"Video {video.title} deleted successfully", "SUCCESS")
        else:
            terminal.print_status(f"Failed to delete video {video.title}", "ERROR")
        
        return success
    
    def print_video_info(self, video_id: int):
        """Print detailed information about a video."""
        video = self.get_video(video_id)
        if not video:
            terminal.print_status(f"Video with ID {video_id} not found", "ERROR")
            return
        
        print(f"\n{'='*50}")
        print(f"Video ID: {video.id}")
        print(f"Title: {video.title}")
        print(f"Status: {video.status}")
        print(f"Created: {video.created_at}")
        
        if video.file_path:
            print(f"File: {video.file_path}")
            if video.file_size:
                print(f"Size: {video.file_size / (1024*1024):.2f} MB")
            if video.duration:
                print(f"Duration: {video.duration:.2f} seconds")
            if video.resolution:
                print(f"Resolution: {video.resolution}")
            if video.fps:
                print(f"FPS: {video.fps}")
        
        # Show prompts
        prompts = self.get_video_prompts(video_id)
        if prompts:
            print(f"\nPrompts ({len(prompts)}):")
            for i, prompt in enumerate(prompts, 1):
                print(f"  {i}. [{prompt.start_time}s, {prompt.duration}s] {prompt.prompt[:50]}...")
        
        # Show recent logs
        logs = self.get_processing_logs(video_id)
        if logs:
            print(f"\nProcessing Logs ({len(logs)} total, showing last 5):")
            for log in logs[-5:]:
                status_symbol = "✓" if log.status == "completed" else "✗" if log.status == "failed" else "○"
                print(f"  {status_symbol} {log.step}: {log.status}")
                if log.message:
                    print(f"    {log.message}")
        
        print(f"{'='*50}\n")
    
    def print_stats(self):
        """Print database statistics."""
        stats = self.db.get_video_stats()
        
        print(f"\n{'='*40}")
        print(f"Video Database Statistics")
        print(f"{'='*40}")
        print(f"Total Videos: {stats['total_videos']}")
        
        if stats['status_counts']:
            print(f"\nBy Status:")
            for status, count in stats['status_counts'].items():
                print(f"  {status}: {count}")
        
        if stats['total_file_size_bytes'] > 0:
            size_mb = stats['total_file_size_bytes'] / (1024 * 1024)
            print(f"\nTotal Storage: {size_mb:.2f} MB")
        
        if stats['total_duration_seconds'] > 0:
            duration_min = stats['total_duration_seconds'] / 60
            print(f"Total Duration: {duration_min:.2f} minutes")
        
        print(f"{'='*40}\n")

# Global video manager instance
video_manager = VideoManager()
