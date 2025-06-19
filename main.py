import os,sys
from openai import AzureOpenAI,OpenAI
from dotenv import load_dotenv
import requests
import yt_dlp
import json
from pydantic import BaseModel
import time
import base64
import subprocess
import argparse
import tempfile
from pydub import AudioSegment
import warnings

warnings.filterwarnings("ignore", category=SyntaxWarning)
load_dotenv()
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")

GPT4O_API_KEY = "2096af94eab44b0bb910def970ad467c"
GPT4O_OPENAI_ENDPOINT = "https://hsh2024.openai.azure.com"
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"
IMAGE_DIR = "./image"



prompt4generate_prompt = """
Given the following transcript data, generate a list of detailed image generation prompts.
- Only generate a prompt when there is a significant scene or visual change needed, not for every line.
- Each prompt should be a dictionary with keys: 'prompt', 'start_time', and 'seconds'.
- 'prompt': a vivid, specific description of the image scene that matches the text and context.
- 'start_time': when the scene should start (in seconds) ,the first image MUST be 0.0.
- dont write any words on the image, just describe the scene.
Ensure the prompts are well-aligned with the transcript timings and content, and only create prompts at appropriate moments where a new visual is needed.
"""

sv_prompt = """
Please break down the following content into several short video scripts for speaking. 
Each script should be suitable for short-form video (e.g. TikTok, YouTube Shorts).
- 60-180 seconds per script.
- You can also output only one script if it is in time(180s).
- Each script should be a dictionary with keys: 'script' and 'tittle'.
- 'script': the content of the script.
- 'tittle': a short video type tittle.

"""

content_prompt = """
You are a video script cleaning assistant. Your task is to refine a transcript by preserving the main content while removing unnecessary parts in english. Please do the following:
- output in english.
- Remove introductory and closing greetings, such as “Hi everyone” or “Thanks for watching.”
- Remove channel promotions, like “Remember to like and subscribe.”
- Remove unrelated small talk or off-topic banter.
- Keep the original wording and tone as much as possible, with minor edits for clarity.
- Output a cleaned and concise version of the script that still feels authentic and natural.
Return only the cleaned script, no additional commentary.

"""
class Prompt(BaseModel):
    prompt: str
    start_time: float

class PromptList(BaseModel):
    prompts: list[Prompt]

class Image(BaseModel):
    path: str
    start_time: float

class Script(BaseModel):
    tittle:str
    script:str

class ScriptList(BaseModel):
    scripts:list[Script]



client = AzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_version="2025-03-01-preview",
)

gpt4o_client = AzureOpenAI(
    api_key=GPT4O_API_KEY,
    azure_endpoint=GPT4O_OPENAI_ENDPOINT,
    api_version="2025-03-01-preview",
)

openai_client = OpenAI(
    api_key=OPENAI_API_KEY
)

def download_yt(url,output_path,format_type="mp3"):
    """
    Download YouTube video as mp3 or mp4
    
    Args:
        url: YouTube URL
        format_type: "mp3" or "mp4"
    """
    # Define fixed output paths based on format type
    
    
    # Create the output directory if it doesn't exist
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Extract filename without extension
    filename = os.path.splitext(os.path.basename(output_path))[0]
    
    if format_type == "mp3":
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',  # Standard quality
            }],
            'outtmpl': filename,  # yt-dlp will add extension automatically
            'keepvideo': False,
            'noplaylist': True,
            'quiet': True,
        }
    else:  # mp4
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': filename,
            'noplaylist': True,
            'quiet': True,
        }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return output_path
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def whisper(path):
    """
    Transcribe audio using Azure OpenAI Whisper, handling large files by splitting if necessary.
    """
    max_size_mb = 24  # Azure OpenAI Whisper limit is 24MB per file
    file_size_mb = os.path.getsize(path) / (1024 * 1024)

    if file_size_mb <= max_size_mb:
        transcribe = client.audio.transcriptions.create(
            file=open(path, "rb"),
            model="whisper",
            response_format="verbose_json",
            timestamp_granularities=["segment"],
        )
        return transcribe
    else:

        audio = AudioSegment.from_file(path)
        chunk_length_ms = int((max_size_mb * 1024 * 1024) / (file_size_mb) * len(audio))  # proportional chunk size
        chunk_length_ms = min(chunk_length_ms, 10 * 60 * 1000)  # max 10 min per chunk for safety

        segments = []
        start = 0
        idx = 0
        while start < len(audio):
            end = min(start + chunk_length_ms, len(audio))
            chunk = audio[start:end]
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmpfile:
                chunk.export(tmpfile.name, format="mp3")
                transcribe = client.audio.transcriptions.create(
                    file=open(tmpfile.name, "rb"),
                    model="whisper",
                    response_format="verbose_json",
                    timestamp_granularities=["segment"],
                )
                # Adjust segment times
                for seg in transcribe.segments:
                    seg.start += start / 1000
                    seg.end += start / 1000
                segments.extend(transcribe.segments)
                os.remove(tmpfile.name)
            start = end
            idx += 1

        # Compose a result-like object
        class Result:
            def __init__(self, segments):
                self.segments = segments
                self.text = " ".join([seg.text for seg in segments])
                self.duration = segments[-1].end if segments else 0

        return Result(segments)

def tts(text,output_path="./output.mp3"):
    # ElevenLabs API endpoint
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}?output_format=mp3_44100_128"
    # Get API key from environment
    api_key = ELEVENLABS_API_KEY
    
    # Headers for the request
    headers = {
        "Xi-Api-Key": api_key,
        "Content-Type": "application/json"
    }
    
    # Data payload
    data = {
        "text": text,
        "model_id": "eleven_multilingual_v2"
    }
    
    try:
        # Make the API request
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()  # Raise exception for HTTP errors
        
        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        # Save the audio file
        with open(output_path, "wb") as f:
            f.write(response.content)
        
        return output_path
    except requests.exceptions.RequestException as e:
        print(f"Error in TTS API request: {e}")
        return None
        
def gpt4o_request(messages,text_format=None):
    try:
        if text_format is not None:
            response = gpt4o_client.responses.parse(
            model="gpt4o",
            input=messages,
            text_format=text_format,
            )
            return response.output_parsed
        else:
            response = gpt4o_client.responses.parse(
            model="gpt4o",
            input=messages,
            )
            return response.output_text
    except Exception as e:
        print(f"Error in GPT-4O request: {e}")
        return "error"
    
def o3_request(messages,text_format=None):
    try:
        if text_format is not None:
            response = client.responses.parse(
            model="o3-mini",
            input=messages,
            text_format=text_format,
            )
            return response.output_parsed
        else:
            response = client.responses.parse(
            model="o3-mini",
            input=messages,
            )
            return response.output_text
    except Exception as e:
        print(f"Error in o3-mini request: {e}")
        return "error"

def generate_image(prompt,output_path="image.jpg"):

    result = openai_client.images.generate(
        model="gpt-image-1",
        size="1024x1024",
        quality="low",
        prompt=prompt
    )

    # Decode the generated image
    image_base64 = result.data[0].b64_json
    image_bytes = base64.b64decode(image_base64)
    
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    with open(output_path, "wb") as f:
        f.write(image_bytes)
    return output_path

def format_timestamp(seconds):
    """Convert seconds to SRT timestamp format (00:00:00,000)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds_remainder = seconds % 60
    milliseconds = int((seconds_remainder - int(seconds_remainder)) * 1000)
    
    return f"{hours:02d}:{minutes:02d}:{int(seconds_remainder):02d},{milliseconds:03d}"

def generate_srt_file(segments, output_path="output.srt"):
    """
    Generate an SRT subtitle file from transcript segments.
    
    Args:
        segments: List of transcript segments with start, end, and text properties
        output_path: Path to save the SRT file
    
    Returns:
        Path to the generated SRT file
    """
    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    with open(output_path, "w", encoding="utf-8") as f:
        for i, segment in enumerate(segments, start=1):
            start_time = segment.start
            end_time = segment.end
            text = segment.text.strip()
            
            # Format timestamps as SRT format (00:00:00,000)
            start_formatted = format_timestamp(start_time)
            end_formatted = format_timestamp(end_time)
            
            # Write the subtitle entry
            f.write(f"{i}\n")
            f.write(f"{start_formatted} --> {end_formatted}\n")
            f.write(f"{text}\n\n")
    
    return output_path

def combine_images(image_list: list[Image], audio_file, output_file, total_duration):
    """Create a video from a list of images and an audio file."""

    # Create a temporary file with ffmpeg directives
    with open("ffmpeg_input.txt", "w") as f:
        for i, img in enumerate(image_list):
            f.write(f"file '{img.path}'\n")
            if i < len(image_list) - 1:
                duration = round(image_list[i+1].start_time - img.start_time, 3)
            else:
                duration = round(total_duration - img.start_time, 3)
                # Ensure last duration is at least 0.1s to avoid ffmpeg errors
                if duration <= 0:
                    duration = 0.1
            f.write(f"duration {duration}\n")
        # Repeat the last image to ensure ffmpeg holds it for the last duration

        f.write(f"file '{image_list[-1].path}'\n")

    cmd = [
        "ffmpeg",
        "-f","concat",
        "-safe", "0",
        "-i", "ffmpeg_input.txt",
        "-i", audio_file,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        output_file
    ]

    subprocess.run(cmd)
    os.remove("ffmpeg_input.txt")  # Clean up temporary file
    print(f"Video successfully created as {output_file}")

def burn_subtitle(video_path, srt_path, output_path):

    cmd = [
        "ffmpeg",
        "-i", video_path,
        "-vf", f"subtitles={srt_path}",
        "-c:a", "copy",
        output_path
    ]
    subprocess.run(cmd, check=True)
    os.remove(video_path)
    os.remove(srt_path)
    print(f"Subtitles burned into video and saved as {output_path}")

def make_video(script,output_path="video/final_video.mp4"):
    print("Generating audio from script...")
    sound_path = "sound.mp3"
    tts(script,output_path=sound_path)

    script_timestamps = whisper(sound_path)
    total_duration = script_timestamps.duration
    script_timestamps = script_timestamps.segments

    generate_srt_file(script_timestamps, output_path="script_timestamps.srt")

    script_for_ai = []
    for segment in script_timestamps:
        script_for_ai.append({
            "start": round(segment.start,1),
            "end": round(segment.end,1),
            "text": segment.text.strip()
        })
    msg =[
        {"role": "system", "content": prompt4generate_prompt  },
        {"role": "user","content": script_for_ai.__str__()}
    ]
    prompt4image = o3_request(msg,PromptList)

    image_list:list[Image] = []

    for i in prompt4image.prompts:
        print(f"Prompt: {i.prompt}, Start Time: {i.start_time}")
    for i in prompt4image.prompts:
        image_path = f"{IMAGE_DIR}/{i.start_time}.jpg"
        generate_image(
            prompt=i.prompt,
            output_path=f"{IMAGE_DIR}/{i.start_time}.jpg"
        )

        image_list.append(Image(
            path=image_path,
            start_time=i.start_time
        ))

    print("Combining images into video...")
    combine_images(image_list, sound_path, "images.mp4", total_duration)
    print("Burning subtitles into video...")
    burn_subtitle("images.mp4", "script_timestamps.srt", output_path=output_path)

    # Remove all files in ./image directory
    if os.path.exists(IMAGE_DIR):
        for filename in os.listdir(IMAGE_DIR):
            file_path = os.path.join(IMAGE_DIR, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)

    os.remove(sound_path)

def main():
    url = input("Enter the ref YouTube URL: ")

    print(f"Downloading reference video from {url}...")
    download_yt(url,output_path="refv_sound.mp3")

    print("Transcribing reference video...")
    ref_text = whisper("refv_sound.mp3")
    os.remove("refv_sound.mp3")
    ref_text = ref_text.text
    print(ref_text)

    writer_msg = [{"role":"system","content":content_prompt},{"role":"user","content":ref_text}]
    
    print("Generating content...")
    content = o3_request(writer_msg)
    print(content)

    sv_writer_msg = [{"role":"system","content":sv_prompt},{"role":"user","content":content}]
    
    # Remove all files in ./video directory before generating new videos
    video_dir = "./video"
    if os.path.exists(video_dir):
        for filename in os.listdir(video_dir):
            file_path = os.path.join(video_dir, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)

    sv_scripts = o3_request(sv_writer_msg,ScriptList)
    for index,i in enumerate(sv_scripts.scripts):
        print(f"Tittle: {i.tittle}, Script: {i.script}")
        make_video(i.script,output_path=f"video/final_video_{index}.mp4")
        
    print("All done!")



if __name__ == "__main__":
    main()