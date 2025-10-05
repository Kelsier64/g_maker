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

class ContentList(BaseModel):
    contents: list[str]

# Database-aware models
class VideoRecord(BaseModel):
    """Model for video records stored in database."""
    id: Optional[int] = None
    title: str
    script: Optional[str] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    duration: Optional[float] = None
    status: str = 'created'
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    