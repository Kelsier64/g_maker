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
- 'start_time': when the scene should start (in seconds) ,the first one should be 0.0.
Ensure the prompts are well-aligned with the transcript timings and content, and only create prompts at appropriate moments where a new visual is needed.
"""

sv_prompt = """
Please break down the following content into several short video scripts for speaking. 
Each script should be suitable for short-form video (e.g. TikTok, YouTube Shorts).
- up to 180 seconds a short video.
- You can also output just one script if it is in time.
- Each script should be a dictionary with keys: 'script' and 'tittle'.
- 'script': the content of the script.
- 'tittle': a short video type tittle.

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
                duration = image_list[i+1].start_time - img.start_time
            else:
                duration = total_duration - img.start_time
            f.write(f"duration {duration}\n")

    # Construct the ffmpeg command
    cmd = [
        "ffmpeg",
        "-f", "concat",
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
    # Clean up temporary file
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
    prompt4image = gpt4o_request(msg,PromptList)
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
    burn_subtitle("images.mp4", "script_timestamps.srt", "final_video.mp4")
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

    writer_msg = [{"role":"system","content":"rewrite the reference text as a spoken script for a youtube video in english,only output the script dont say other thing"},{"role":"user","content":ref_text}]
    
    print("Generating script...")
    script = gpt4o_request(writer_msg)
    print(script)

    sv_writer_msg = [{"role":"system","content":sv_prompt},{"role":"user","content":script}]
    
    sv_scripts = gpt4o_request(sv_writer_msg,ScriptList)
    for index,i in enumerate(sv_scripts.scripts):
        print(f"Tittle: {i.tittle}, Script: {i.script}")
        make_video(i.script,output_path=f"video/final_video_{index}.mp4")

    print("All done!")


    
if __name__ == "__main__":
    main()