from pydantic import BaseModel

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


    