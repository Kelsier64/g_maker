from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class Prompt(BaseModel):
    prompt: str
    start_time: float
    duration: int

class PromptList(BaseModel):
    prompts: list[Prompt]

class Video(BaseModel):
    path: str
    start_time: float
    duration: int

class Script(BaseModel):
    title: str
    script: str

class ScriptList(BaseModel):
    scripts: list[Script]

# Database-aware models
class VideoRecord(BaseModel):
    """Model for video records stored in database."""
    id: Optional[int] = None
    title: str
    script: Optional[str] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    duration: Optional[float] = None
    fps: Optional[int] = None
    resolution: Optional[str] = None
    status: str = 'created'
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None

class VideoPrompt(BaseModel):
    """Model for prompts associated with videos."""
    id: Optional[int] = None
    video_id: int
    prompt: str
    start_time: float
    duration: int
    created_at: Optional[datetime] = None

class ProcessingLog(BaseModel):
    """Model for processing logs."""
    id: Optional[int] = None
    video_id: int
    step: str
    status: str  # 'started', 'completed', 'failed'
    message: Optional[str] = None
    timestamp: Optional[datetime] = None


    