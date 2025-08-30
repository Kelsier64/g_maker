import os
from pathlib import Path
from typing import Optional, Dict, Any
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from ..config import PATHS
from ..utils.terminal import print_status, print_separator

"""YouTube upload service for G-Maker AI Video Generator."""





# YouTube API scopes
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

# YouTube API service name and version
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"


class YouTubeUploader:
    """Handles YouTube video uploads with OAuth2 authentication."""
    
    def __init__(self, credentials_file: Optional[str] = None, token_file: Optional[str] = None):
        """Initialize YouTube uploader.
        
        Args:
            credentials_file: Path to OAuth2 credentials JSON file
            token_file: Path to store/load OAuth2 token
        """
        self.credentials_file = credentials_file or os.path.join(PATHS["CONFIG"], "client_secret.json")
        self.token_file = token_file or os.path.join(PATHS["CONFIG"], "youtube_token.json")
        self.youtube = None
        
    def authenticate(self) -> bool:
        """Authenticate with YouTube API using OAuth2.
        
        Returns:
            bool: True if authentication successful
        """
        creds = None
        
        # Load existing token
        if os.path.exists(self.token_file):
            try:
                creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
            except Exception as e:
                print_status(f"Error loading token: {e}", "WARNING")
        
        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print_status(f"Error refreshing token: {e}", "WARNING")
                    creds = None
            
            if not creds:
                if not os.path.exists(self.credentials_file):
                    print_status(f"Credentials file not found: {self.credentials_file}", "ERROR")
                    return False
                
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, SCOPES
                    )
                    creds = flow.run_local_server(port=8080)
                except Exception as e:
                    print_status(f"OAuth2 flow failed: {e}", "ERROR")
                    return False
            
            # Save credentials for next time
            try:
                with open(self.token_file, 'w') as token:
                    token.write(creds.to_json())
            except Exception as e:
                print_status(f"Error saving token: {e}", "WARNING")
        
        try:
            self.youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, credentials=creds)
            print_status("YouTube API authentication successful", "SUCCESS")
            return True
        except Exception as e:
            print_status(f"Error building YouTube service: {e}", "ERROR")
            return False
    
    def upload_video(
        self,
        video_path: str,
        title: str,
        description: str = "",
        tags: Optional[list] = None,
        category_id: str = "22",  # People & Blogs
        privacy_status: str = "private",
        thumbnail_path: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Upload video to YouTube.
        
        Args:
            video_path: Path to video file
            title: Video title
            description: Video description
            tags: List of video tags
            category_id: YouTube category ID
            privacy_status: "private", "public", "unlisted", or "public"
            thumbnail_path: Optional path to thumbnail image
            
        Returns:
            Dict with upload response or None if failed
        """
        if not self.youtube:
            if not self.authenticate():
                return None
        
        if not os.path.exists(video_path):
            print_status(f"Video file not found: {video_path}", "ERROR")
            return None
        
        print_separator("YouTube Upload")
        print_status(f"Uploading: {Path(video_path).name}", "PROCESSING")
        
        # Prepare video metadata
        body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags or [],
                "categoryId": category_id
            },
            "status": {
                "privacyStatus": privacy_status
            }
        }
        
        # Create media upload object
        media = MediaFileUpload(
            video_path,
            chunksize=-1,  # Upload in single chunk
            resumable=True
        )
        
        try:
            # Execute upload
            insert_request = self.youtube.videos().insert(
                part=",".join(body.keys()),
                body=body,
                media_body=media
            )
            
            response = None
            error = None
            retry = 0
            
            while response is None:
                try:
                    status, response = insert_request.next_chunk()
                    if status:
                        print_status(f"Upload progress: {int(status.progress() * 100)}%", "PROCESSING")
                except HttpError as e:
                    if e.resp.status in [500, 502, 503, 504]:
                        error = f"Retriable HTTP error: {e}"
                        retry += 1
                        if retry > 3:
                            print_status(f"Max retries exceeded: {error}", "ERROR")
                            return None
                    else:
                        print_status(f"HTTP error: {e}", "ERROR")
                        return None
                except Exception as e:
                    print_status(f"Upload error: {e}", "ERROR")
                    return None
            
            if response:
                video_id = response["id"]
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                print_status(f"Upload successful! Video ID: {video_id}", "SUCCESS")
                print_status(f"Video URL: {video_url}", "SUCCESS")
                
                # Upload thumbnail if provided
                if thumbnail_path and os.path.exists(thumbnail_path):
                    self._upload_thumbnail(video_id, thumbnail_path)
                
                return {
                    "id": video_id,
                    "url": video_url,
                    "title": title,
                    "status": privacy_status
                }
        
        except Exception as e:
            print_status(f"Upload failed: {e}", "ERROR")
            return None
    
    def _upload_thumbnail(self, video_id: str, thumbnail_path: str) -> bool:
        """Upload thumbnail for video.
        
        Args:
            video_id: YouTube video ID
            thumbnail_path: Path to thumbnail image
            
        Returns:
            bool: True if successful
        """
        try:
            media = MediaFileUpload(thumbnail_path)
            self.youtube.thumbnails().set(
                videoId=video_id,
                media_body=media
            ).execute()
            print_status("Thumbnail uploaded successfully", "SUCCESS")
            return True
        except Exception as e:
            print_status(f"Thumbnail upload failed: {e}", "WARNING")
            return False
    
    def get_video_info(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Get information about uploaded video.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Dict with video information or None if failed
        """
        if not self.youtube:
            if not self.authenticate():
                return None
        
        try:
            response = self.youtube.videos().list(
                part="snippet,status,statistics",
                id=video_id
            ).execute()
            
            if response["items"]:
                return response["items"][0]
            else:
                print_status(f"Video not found: {video_id}", "ERROR")
                return None
                
        except Exception as e:
            print_status(f"Error getting video info: {e}", "ERROR")
            return None


def upload_video_to_youtube(
    video_path: str,
    title: str,
    description: str = "",
    tags: Optional[list] = None,
    privacy_status: str = "private"
) -> Optional[str]:
    """Convenience function to upload video to YouTube.
    
    Args:
        video_path: Path to video file
        title: Video title
        description: Video description
        tags: List of video tags
        privacy_status: Video privacy setting
        
    Returns:
        YouTube video URL if successful, None otherwise
    """
    uploader = YouTubeUploader()
    result = uploader.upload_video(
        video_path=video_path,
        title=title,
        description=description,
        tags=tags,
        privacy_status="public"
    )
    
    return result["url"] if result else None