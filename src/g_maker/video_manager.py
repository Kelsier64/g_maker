import os
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
import cv2

from g_maker.database import db
from g_maker.models import VideoRecord
from g_maker.utils import terminal
from g_maker.services.yt_uploader import YouTubeUploader

class VideoManager:
    """High-level manager for video operations with database integration."""
    
    def __init__(self):
        self.db = db
    
    def create_video_project(self, title: str, script: str) -> int:
        """Create a new video project and return its ID."""
        terminal.print_status(f"Creating video project: {title}", "PROCESSING")
        
        # Create video record
        video_id = self.db.create_video_record(title=title, script=script)
        
        terminal.print_status(f"Video project created with ID: {video_id}", "SUCCESS")
        return video_id
    
    def start_processing(self, video_id: int, step: str, message: str = None):
        """Mark the start of a processing step."""
        self.db.update_video_info(video_id, status="processing")
    
    
    
    def complete_processing_step(self, video_id: int, step: str, message: str = None):
        """Mark the completion of a processing step."""
        pass  # Individual steps don't change status, only final completion does
    
    def fail_processing_step(self, video_id: int, step: str, error_message: str):
        """Mark the failure of a processing step."""
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
            status="completed"
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
            # Parse metadata if it exists (keeping for backward compatibility)
            if data.get('metadata'):
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
            # Parse metadata if it exists (keeping for backward compatibility)
            if data.get('metadata'):
                try:
                    data['metadata'] = json.loads(data['metadata']) if isinstance(data['metadata'], str) else data['metadata']
                except json.JSONDecodeError:
                    data['metadata'] = {}
            videos.append(VideoRecord(**data))
        
        return videos
        
        return videos
    
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
    
    def upload_to_youtube(self, video_id: int, title: str = None, description: str = "", 
                         tags: List[str] = None, privacy_status: str = "private") -> Optional[str]:
        """Upload video to YouTube and update database with upload info."""
        video = self.get_video(video_id)
        if not video:
            terminal.print_status(f"Video with ID {video_id} not found", "ERROR")
            return None
        
        if not video.file_path or not os.path.exists(video.file_path):
            terminal.print_status(f"Video file not found: {video.file_path}", "ERROR")
            return None
        
        # Use video title if none provided
        upload_title = title or video.title
        
        try:
            uploader = YouTubeUploader()
            result = uploader.upload_video(
                video_path=video.file_path,
                title=upload_title,
                description=description,
                tags=tags,
                privacy_status=privacy_status
            )
            
            if result:
                # Mark video as uploaded
                self.db.update_video_info(video_id, status="uploaded")
                terminal.print_status(f"✅ Video uploaded to YouTube: {result['url']}", "SUCCESS")
                return result['url']
            else:
                terminal.print_status("Upload failed", "ERROR")
                return None
                
        except Exception as e:
            error_msg = f"Upload error: {str(e)}"
            terminal.print_status(error_msg, "ERROR")
            return None
    
    def get_upload_details_interactive(self, video: VideoRecord) -> Dict[str, Any]:
        """Get upload details from user interactively."""
        terminal.print_separator(f"YouTube Upload - {video.title}")
        
        # Get title
        title = terminal.get_user_input("Video title", video.title, required=True)
        
        # Get description
        description = terminal.get_user_input("Video description", "", required=False)
        
        # Get tags
        tags_input = terminal.get_user_input("Tags (comma-separated)", "", required=False)
        tags = [tag.strip() for tag in tags_input.split(",") if tag.strip()] if tags_input else []
        
        # Get privacy status
        print("\nPrivacy options:")
        print("1. Private (default)")
        print("2. Unlisted") 
        print("3. Public")
        privacy_choice = terminal.get_user_input("Privacy setting", "1", required=True)
        
        privacy_map = {"1": "private", "2": "unlisted", "3": "public"}
        privacy_status = privacy_map.get(privacy_choice, "private")
        
        return {
            "title": title,
            "description": description,
            "tags": tags,
            "privacy_status": privacy_status
        }

# Global video manager instance
video_manager = VideoManager()
