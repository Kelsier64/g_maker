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

import src.t2v_api_client as t2v_api_client
import src.make_speaker as make_speaker
from uuid import uuid4

warnings.filterwarnings("ignore", category=SyntaxWarning)
load_dotenv()
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")

GPT4O_API_KEY = "2096af94eab44b0bb910def970ad467c"
GPT4O_OPENAI_ENDPOINT = "https://hsh2024.openai.azure.com"
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

VOICE_ID = "MFZUKuGQUsGJPQjTS4wC"
VIDEO_FPS = 16

# Add a single global PATHS dict for all built-in paths
PATHS = {
    "GENERATED_VIDEOS_DIR": "./generated_videos",
    "FINAL_VIDEOS_DIR": "./final_videos",
    "TEMP_DIR": "./temp",
    "SOUND_PATH": "temp/sound.mp3",
    "BASE_VIDEO": "temp/base_video.mp4",
    "COMBINED_VIDEO": "temp/combined_video.mp4",
    "REF_SOUND": "temp/refv_sound.mp3",
    "SRT": "temp/script_timestamps.srt",
    "CLOSE_JPG": "static/close.jpg",
    "OPEN_JPG": "static/open.jpg"

}


prompt4generate_prompt = """
Given the following transcript data, generate a list of detailed image generation prompts.
- Only generate a prompt when there is a significant scene or visual change needed, not for every line.
- Each prompt should be a dictionary with keys: 'prompt', 'start_time', and 'seconds'.
- 'prompt': a vivid, specific description of the image scene that matches the text and context.
- 'start_time': when the scene should start (in seconds) ,the first image MUST be 0.0.
- dont write any words on the image, just describe the scene.
Ensure the prompts are well-aligned with the transcript timings and content, and only create prompts at appropriate moments where a new visual is needed.
"""
prompt4generate_prompt = """
You are given a transcript with timestamps.
Your task: generate a list of video generation prompts for a text-to-video system.
Rules:
1. Only create a prompt when there is a **significant scene or visual change** — NOT for every dialogue line.
2. Ensure prompts are **aligned with transcript timings** and only capture **meaningful visual transitions**.
3. videos don't need to stick together.
4. dont make a video while the previous one is in duration.
5. dont write any words on the image, just describe the scene.
6. the video generation model is poor ,so keep the prompts simple and focused.
7. no timeline graphic or chart or other overlays.
Output format:
   - "prompt": a vivid scene description matching the transcript and context.
   - "start_time": float, scene start time in seconds.
   - "duration": integer, duration of the scene in seconds.(max:15)

"""

sv_prompt = """
you are a expert script writer
Please break down the following content into one or several short-form video scripts suitable for platforms like TikTok or YouTube Shorts.

Requirements:
- Each script should be less than 180 seconds in total.
- Each script should be self-contained and understandable without prior context.
- Each script should have enough content.
- You can output just one script if the content fits within the 180-second limit.
- Each output should be a dictionary with the following keys:
  - 'title': A short, catchy video title.
  - 'script': The full narration for the video, written in a natural, spoken tone.

Script Writing Guidelines:
- The tone should be conversational, energetic, and easy to follow.
- Use short sentences, rhetorical questions, and emotional hooks to keep viewers engaged.
- Start strong — grab attention within the first few seconds,the hook at the start should be eye-catching and intriguing.
- End with a thought-provoking idea or light call to action (e.g. "What do you think?" or "Share this with a friend").
- Avoid formal or academic wording.

"""

content_prompt = """
You are a video script cleaning assistant. Your task is to refine a transcript by preserving the main content while removing unnecessary parts. Please do the following:
- translate to english.
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
    
def gpt_request(messages,text_format=None):
    try:
        if text_format is not None:
            response = client.responses.parse(
            model="o4-mini",
            input=messages,
            text_format=text_format,
            )
            return response.output_parsed
        else:
            response = client.responses.parse(
            model="o4-mini",
            input=messages,
            )
            return response.output_text
    except Exception as e:
        print(f"Error in o4-mini request: {e}")
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

def burn_subtitle(input_video_path,srt_path,output_path):

    cmd = [
        "ffmpeg",
        "-i", input_video_path,
        "-vf", f"subtitles={srt_path}",
        "-c:a", "copy",
        output_path
    ]
    subprocess.run(cmd, check=True)
    print(f"Subtitles burned into video and saved as {output_path}")

def combine_videos(base_video_path: str, video_list: list[Video], audio_path: str, output_path: str):
    """
    Combine base video with overlay videos using ffmpeg.
    Each overlay is enabled during between(start_time, start_time+duration).
    The provided audio_path is mapped to the output (replacing any base audio).
    """
    # Build input arguments: base video, overlay videos, then audio
    inputs = ["-y", "-i", base_video_path]
    for v in video_list:
        inputs += ["-i", v.path]
    inputs += ["-i", audio_path]

    # Build filter_complex: first reset overlay timestamps with setpts, then overlay them.
    filter_parts = []
    prev_label = "[0:v]"
    for idx, v in enumerate(video_list, start=1):
        inp_label = f"[{idx}:v]"
        ov_label = f"[ov{idx}]"
        out_label = f"[v{idx}]"
        start = float(v.start_time)
        end = float(v.start_time + v.duration)
        # reset overlay timestamps so the overlay plays from its own t=0,
        # shifted to start seconds on the main timeline
        filter_parts.append(f"{inp_label} setpts=PTS-STARTPTS+{start}/TB {ov_label}")
        # overlay the prepared overlay; enable only during the time window
        filter_parts.append(f"{prev_label}{ov_label} overlay=(W-w)/2:(H-h)/2:enable='between(t,{start},{end})' {out_label}")
        prev_label = out_label

    ff_filter = ";".join(filter_parts) if filter_parts else None

    # Determine final video stream map
    if ff_filter:
        filter_args = ["-filter_complex", ff_filter]
        map_video = ["-map", prev_label]
    else:
        filter_args = []
        map_video = ["-map", "0:v"]

    # Audio input index is base (0) + overlays (len(video_list)) => next is len(video_list)+1
    audio_input_index = len(video_list) + 1
    map_audio = ["-map", f"{audio_input_index}:a"]

    # Output encoding / options
    encoding_opts = [
        "-r", str(VIDEO_FPS),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest"
    ]

    cmd = ["ffmpeg"] + inputs + filter_args + encoding_opts + map_video + map_audio + [output_path]

    try:
        proc = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except subprocess.CalledProcessError as e:
        # show ffmpeg output for debugging, then raise a clearer error
        print("ffmpeg stdout:\n", e.stdout)
        print("ffmpeg stderr:\n", e.stderr)
        raise RuntimeError("ffmpeg failed, see stderr above") from e

def make_video(script,output_path):
    print("Generating audio...")
    tts(script,output_path=PATHS["SOUND_PATH"])

    make_speaker.create_speaker_video(
        mp3_path=PATHS["SOUND_PATH"],
        closed_mouth_jpg=PATHS["CLOSE_JPG"],
        open_mouth_jpg=PATHS["OPEN_JPG"],
        output_path=PATHS["BASE_VIDEO"]
    )
    print("Generating srt...")
    script_timestamps = whisper(PATHS["SOUND_PATH"])
    script_timestamps = script_timestamps.segments

    generate_srt_file(script_timestamps, output_path=PATHS["SRT"])

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
    print("Generating prompts for video generation...")
    prompt4video = gpt_request(msg,PromptList)

    video_list: list[Video] = []
    task_map = {}
    
    # Submit all video generation tasks and map task_id to video info
    for prompt in prompt4video.prompts:
        print(f"Prompt: {prompt.prompt}, Start Time: {prompt.start_time}, Duration: {prompt.duration}")
        video_path = f"{PATHS['GENERATED_VIDEOS_DIR']}/{prompt.start_time}_{prompt.duration}.mp4"
        task_id = t2v_api_client.submit_video_generation(
            prompt=prompt.prompt,
            sample_steps=50,
            fps=VIDEO_FPS,
            num_frames=prompt.duration * VIDEO_FPS + 1,
        )
        if task_id:
            task_map[task_id] = {
                "video_path": video_path,
                "start_time": prompt.start_time,
                "duration": prompt.duration
            }
        time.sleep(0.5)

    # Monitor and download videos as they complete
    for task_id, info in task_map.items():
        video_filename = t2v_api_client.monitor_task(task_id)
        if not video_filename:
            breakpoint()
        t2v_api_client.download_video(video_filename, output_path=info["video_path"])
        video_list.append(Video(
            path=info["video_path"],
            start_time=info["start_time"],
            duration=info["duration"]
        ))

    print("Combining videos into final video...")
    combine_videos(PATHS["BASE_VIDEO"], video_list, PATHS["SOUND_PATH"], PATHS["COMBINED_VIDEO"])
    print("Burning subtitles into video...")
    burn_subtitle(PATHS["COMBINED_VIDEO"], PATHS["SRT"], output_path=output_path)

def init():
    if os.path.exists(PATHS["GENERATED_VIDEOS_DIR"]):
        for filename in os.listdir(PATHS["GENERATED_VIDEOS_DIR"]):
            file_path = os.path.join(PATHS["GENERATED_VIDEOS_DIR"], filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
    else:
        os.makedirs(PATHS["GENERATED_VIDEOS_DIR"])

    if os.path.exists(PATHS["TEMP_DIR"]):
        for filename in os.listdir(PATHS["TEMP_DIR"]):
            file_path = os.path.join(PATHS["TEMP_DIR"], filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
    else:
        os.makedirs(PATHS["TEMP_DIR"])


def pipeline(url):
    print(f"Downloading reference video from {url}...")
    download_yt(url, output_path=PATHS["REF_SOUND"])

    print("\n")
    print("="*20)
    print("\n")
    print("Transcribing reference video...")
    ref_text = whisper(PATHS["REF_SOUND"])
    os.remove(PATHS["REF_SOUND"])
    ref_text = ref_text.text
    print(ref_text)

    writer_msg = [{"role": "system", "content": content_prompt}, {"role": "user", "content": ref_text}]


    print("\n")
    print("="*20)
    print("\n")
    print("Generating content...")
    content = gpt_request(writer_msg)
    print(content)
    print("\n")
    print("="*20)
    print("\n")
    sv_writer_msg = [{"role": "system", "content": sv_prompt}, {"role": "user", "content": content}]
    print("Generating short video scripts...")
    sv_scripts = gpt_request(sv_writer_msg, ScriptList)


    # video making loop
    details_path = os.path.join(PATHS["FINAL_VIDEOS_DIR"], "video_details.txt")
    uid = uuid4().hex
    with open(details_path, "w", encoding="utf-8") as details_file:
        details_file.write(f"Series uid: {uid}, Source: {url}\n")

        for index, i in enumerate(sv_scripts.scripts):
            
            print(f"Title: {i.title}, Script: {i.script}")
            print("="*20)
            init()

            output_file = os.path.join(PATHS["FINAL_VIDEOS_DIR"], f"{uid}_{index}.mp4")
            
            start = time.perf_counter()
            make_video(i.script, output_path=output_file)
            elapsed = time.perf_counter() - start
            details_file.write(f"   Video: {index}, Title: {i.title}, FileName: {output_file}, ElapsedSeconds:{elapsed:.2f}\n")

    print(f"\nseries {uid} done")


def main():
    # init
    t2v_api_client.clean_queue()
    t2v_api_client.clean_all_video()


    while True:
        urls = []
        while True:
            print("1. Add a YouTube URL")
            print("2. Add multiple YouTube URLs (comma-separated)")
            print("3. Start processing")
            choice = input("Enter your choice: ").strip()

            if choice == "1":
                u = input("Enter the YouTube URL: ").strip()
                if u:
                    urls.append(u)
                    print("Added.")
                else:
                    print("No URL entered.")
            elif choice == "2":
                s = input("Enter URLs separated by commas: ").strip()
                new_urls = [x.strip() for x in s.split(",") if x.strip()]
                if new_urls:
                    urls.extend(new_urls)
                    print(f"Added {len(new_urls)} URLs.")
                else:
                    print("No URLs entered.")
            elif choice == "3":
                if not urls:
                    print("No URLs provided. Please add at least one URL.")
                    continue
                print("Starting processing of URLs...")
                break
            else:
                print("Invalid choice, please try again.")

        for idx, url in enumerate(urls):
            try:
                print(f"\nProcessing URL {idx + 1}/{len(urls)}: {url}")
                pipeline(url)
            except Exception as e:
                print(f"Error processing {url}: {e}")

        print("All done.")

if __name__ == "__main__":
    main()