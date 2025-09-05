import sqlite3
import os
from datetime import datetime
from typing import List, Optional, Dict, Any
from contextlib import contextmanager
from g_maker.config import PATHS

class VideoDatabase:
    """SQLite database manager for output videos and related metadata."""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            # Find the project root by looking for pyproject.toml
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = current_dir
            
            # Walk up the directory tree to find pyproject.toml
            while project_root != os.path.dirname(project_root):  # Stop at filesystem root
                if os.path.exists(os.path.join(project_root, "pyproject.toml")):
                    break
                project_root = os.path.dirname(project_root)
            
            db_path = os.path.join(project_root, "videos.db")
        
        self.db_path = db_path
        self.init_database()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
        try:
            yield conn
        finally:
            conn.close()
    
    def init_database(self):
        """Initialize the database with required tables."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create videos table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS videos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    script TEXT,
                    file_path TEXT,
                    file_size INTEGER,
                    duration REAL,
                    status TEXT DEFAULT 'created',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_videos_created_at ON videos(created_at)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_videos_status ON videos(status)')
            
            conn.commit()
    
    def create_video_record(self, title: str, script: str, file_path: str = None) -> int:
        """Create a new video record and return its ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO videos (title, script, file_path)
                VALUES (?, ?, ?)
            ''', (title, script, file_path))
            
            conn.commit()
            return cursor.lastrowid
    
    def update_video_info(self, video_id: int, file_path: str = None, file_size: int = None,
                         duration: float = None, status: str = None):
        """Update video information."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            updates = []
            params = []
            
            if file_path is not None:
                updates.append("file_path = ?")
                params.append(file_path)
            if file_size is not None:
                updates.append("file_size = ?")
                params.append(file_size)
            if duration is not None:
                updates.append("duration = ?")
                params.append(duration)
            if status is not None:
                updates.append("status = ?")
                params.append(status)
            
            if updates:
                updates.append("updated_at = CURRENT_TIMESTAMP")
                params.append(video_id)
                
                query = f"UPDATE videos SET {', '.join(updates)} WHERE id = ?"
                cursor.execute(query, params)
                conn.commit()
    
    def get_video(self, video_id: int) -> Optional[Dict[str, Any]]:
        """Get a video record by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM videos WHERE id = ?', (video_id,))
            row = cursor.fetchone()
            
            if row:
                return dict(row)
            return None
    
    def get_videos(self, status: str = None, limit: int = None) -> List[Dict[str, Any]]:
        """Get videos, optionally filtered by status."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = 'SELECT * FROM videos'
            params = []
            
            if status:
                query += ' WHERE status = ?'
                params.append(status)
            
            query += ' ORDER BY created_at DESC'
            
            if limit:
                query += ' LIMIT ?'
                params.append(limit)
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def delete_video(self, video_id: int) -> bool:
        """Delete a video record and its associated data."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if video exists
            cursor.execute('SELECT file_path FROM videos WHERE id = ?', (video_id,))
            row = cursor.fetchone()
            
            if not row:
                return False
            
            # Delete the video file if it exists
            file_path = row['file_path']
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except OSError:
                    pass  # File might be in use or permissions issue
            
            # Delete database record
            cursor.execute('DELETE FROM videos WHERE id = ?', (video_id,))
            conn.commit()
            
            return cursor.rowcount > 0
    
    def get_video_stats(self) -> Dict[str, Any]:
        """Get statistics about videos in the database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Total videos
            cursor.execute('SELECT COUNT(*) as total FROM videos')
            total = cursor.fetchone()['total']
            
            # Videos by status
            cursor.execute('''
                SELECT status, COUNT(*) as count 
                FROM videos 
                GROUP BY status
            ''')
            status_counts = {row['status']: row['count'] for row in cursor.fetchall()}
            
            # Total file size
            cursor.execute('SELECT SUM(file_size) as total_size FROM videos WHERE file_size IS NOT NULL')
            total_size = cursor.fetchone()['total_size'] or 0
            
            # Total duration
            cursor.execute('SELECT SUM(duration) as total_duration FROM videos WHERE duration IS NOT NULL')
            total_duration = cursor.fetchone()['total_duration'] or 0
            
            return {
                'total_videos': total,
                'status_counts': status_counts,
                'total_file_size_bytes': total_size,
                'total_duration_seconds': total_duration
            }

# Global database instance
db = VideoDatabase()
