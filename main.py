import os,sys
from openai import AzureOpenAI
from dotenv import load_dotenv
import requests
import yt_dlp
import json
from pydantic import BaseModel
import time
import subprocess
import argparse
load_dotenv()
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")

GPT4O_API_KEY = "2096af94eab44b0bb910def970ad467c"
GPT4O_OPENAI_ENDPOINT = "https://hsh2024.openai.azure.com"
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"

  
prompt4generate_prompt = """
Given the following transcript data, generate a list of detailed video generation prompts.
- Only generate a prompt when there is a significant scene or visual change needed, not for every line.
- Each prompt should be a dictionary with keys: 'prompt', 'start_time', and 'seconds'.
- 'prompt': a vivid, specific description of the video scene that matches the text and context.
- 'start_time': when the scene should start (in seconds).
- 'seconds': the duration of the scene (in seconds), and must not exceed 5 seconds for any prompt.
Ensure the prompts are well-aligned with the transcript timings and content, and only create prompts at appropriate moments where a new visual is needed.
"""

test_script = """
Hey, did you know the Great Pyramid of Giza was the tallest structure on Earth for over 3,800 years? Built without modern machines—just manpower, math, and mystery. Let’s dive in!

The Pyramids of Egypt—especially the Great Pyramid—are one of the Seven Wonders of the Ancient World. Built over 4,500 years ago during the reign of Pharaoh Khufu, this massive stone structure originally stood 146 meters tall. That's roughly a 45-story building!

It's made from over 2 million limestone and granite blocks. Each block can weigh up to 80 tons. And here's the wild part: we still don't fully understand how they moved and stacked them so precisely.

So how’d they build it? There are a few theories:

First, the Ramp Theory—maybe they used long ramps made of mudbrick and limestone.
Second, the Spiral Theory—some think ramps spiraled around the pyramid as it rose.
And third, the Internal Spiral Theory—a newer idea that suggests a hidden inner ramp helped workers build it from the inside out.

Still no solid proof for any of them, which makes it even more fascinating.

In 2017, scientists discovered a mysterious hidden void inside the Great Pyramid using cosmic ray technology. No one knows what’s in it… yet.

Also, the alignment of the pyramid is insanely accurate. It’s almost perfectly aligned with true North, South, East, and West—with less than 0.05 degrees of error. Try doing that without GPS.

Quick facts:

The pyramid was originally covered in polished white limestone that reflected the sun like a mirror.

The builders weren’t slaves—they were skilled laborers, well-fed and respected.

Some believe the pyramid's proportions match the Golden Ratio. Coincidence… or design?

Whether it’s math, mystery, or just pure human genius, the pyramids remain one of the greatest achievements in history.

If you learned something new, hit like and follow for more history in under 3 minutes!

"""

test_config = {
    "content_url": "https://youtu.be/dQw4w9WgXcQ",
    "bgv_url": "https://youtu.be/dQw4w9WgXcQ",
    "bgm_url": "https://youtu.be/dQw4w9WgXcQ"
}


class Prompt(BaseModel):
    prompt: str
    start_time: float
    seconds: int

class PromptList(BaseModel):
    prompts: list[Prompt]

class Video(BaseModel):
    video_path: str
    start_time: float
    seconds: int
    


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


def download_yt(url, output_path, format_type="mp3"):
    """
    Download YouTube video as mp3 or mp4
    
    Args:
        url: YouTube URL
        output_path: Full path to save the downloaded file (e.g., "./output/audio.mp3")
        format_type: "mp3" or "mp4"
    """
    # Create the output directory if it doesn't exist
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Extract filename without extension from the provided output_path
    filename_template = os.path.join(output_dir, os.path.splitext(os.path.basename(output_path))[0])
    
    if format_type == "mp3":
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',  # Standard quality
            }],
            'outtmpl': filename_template + '.%(ext)s', # Use template for yt-dlp
            'keepvideo': False,
            'noplaylist': True,
            'quiet': True,
        }
    else:  # mp4
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': filename_template + '.%(ext)s', # Use template for yt-dlp
            'noplaylist': True,
            'quiet': True,
        }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        # Check if the exact output_path exists
        if os.path.exists(output_path):
            return output_path
        else:
            print(f"Warning: Expected output file {output_path} not found directly. yt-dlp might have saved with a slightly different name or extension.")

            return output_path


    except Exception as e:
        print(f"An error occurred during download: {e}")
        return None

def whisper(path):

    transcribe = client.audio.transcriptions.create(
        file=open(path, "rb"),
        model="whisper",
        response_format="verbose_json",
        timestamp_granularities=["segment"],
    )
    return transcribe

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

def combine_media(video_file, audio_file, srt_file, output_file):
    """Combine video and audio files with subtitles from timestamps using NVENC hardware acceleration."""
    
    # Combine video and audio with subtitles using NVENC
    cmd = [
        "ffmpeg",
        "-i", video_file,  # Input video
        "-i", audio_file,  # Input audio
        "-c:v", "h264_nvenc",  # Use NVIDIA hardware acceleration
        "-preset", "p4",    # NVENC preset (p1=slow/best quality, p7=fast/lower quality)
        "-rc:v", "vbr",     # Variable bitrate mode
        "-cq:v", "18",      # Quality level (lower = better)
        "-map", "0:v:0",    # Map video from first input
        "-map", "1:a:0",    # Map audio from second input
        "-vf", f"subtitles={srt_file}",  # Burn subtitles into video
        "-c:a", "aac",      # Use AAC for audio codec
        "-b:a", "192k",     # Audio bitrate
        "-shortest",        # End with shortest stream
        output_file         # Output file
    ]
    
    print("Executing FFmpeg command with NVENC hardware acceleration...")
    subprocess.run(cmd)
    


def main(url):
    # download_yt(url,output_path="ref.mp3")
    download_yt(url,output_path="bgv.mp4", format_type="mp4")
    # ref_text = whisper("sound.mp3")
    # ref_text = ref_text.text
    # print(ref_text)
    # writer_msg = [{"role":"system","content":"rewrite the reference text as a spoken script for a youtube video,only output the script dont say other thing"},{"role":"user","content":ref_text}]
    # script = gpt4o_request(writer_msg)
    # print(script)
    script = test_script

    # tts(script)
    script_timestamps = whisper("output.mp3")
    script_timestamps = script_timestamps.segments
      
    # Save script_timestamps to a file
    generate_srt_file(script_timestamps, output_path="script_timestamps.srt")
    time.sleep(3)
    # Combine the video, audio, and timestamps
    combine_media("bgv.mp4", "output.mp3", "script_timestamps.srt", "final_output.mp4")


if __name__ == "__main__":
    main("https://youtu.be/XBIaqOm0RKQ?si=up1DNPIAiImD4152")