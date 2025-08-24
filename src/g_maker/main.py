import os
from openai import AzureOpenAI,OpenAI
from dotenv import load_dotenv
import requests

from pydantic import BaseModel
import time
import tempfile
from pydub import AudioSegment
import warnings
from uuid import uuid4
import sys
from datetime import datetime
import threading

from g_maker.services import t2v_api_client
from g_maker.processing import make_speaker
from g_maker.processing import video_processing
from g_maker.processing import srt_processing
from g_maker.input import downloader
from g_maker.models import Prompt,PromptList,Video,Script,ScriptList


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
    "FINAL_VIDEOS_DIR": "./output",
    "TEMP_DIR": "./temp",
    "AUDIO_PATH": "./temp/audio.mp3",
    "BASE_VIDEO": "./temp/base_video.mp4",
    "COMBINED_VIDEO": "./temp/combined_video.mp4",
    "BLURRED_VIDEO": "./temp/blurred_video.mp4",
    "REF_AUDIO": "./temp/ref_audio.mp3",
    "SRT": "./temp/script_timestamps.srt",
    "CLOSE_JPG": "./static/close.jpg",
    "OPEN_JPG": "./static/open.jpg",
}

# Terminal output utilities
class ProgressBar:
    def __init__(self, total, description="Progress", width=50):
        self.total = total
        self.current = 0
        self.description = description
        self.width = width
        self.start_time = time.time()
        
    def update(self, progress=1):
        self.current += progress
        self._draw()
        
    def set_progress(self, current):
        self.current = current
        self._draw()
        
    def _draw(self):
        if self.total == 0:
            percent = 100
        else:
            percent = min(100, (self.current / self.total) * 100)
        
        filled_width = int(self.width * percent / 100)
        bar = "█" * filled_width + "░" * (self.width - filled_width)
        
        sys.stdout.write(f"\r{self.description}: |{bar}| {percent:.1f}%")
        sys.stdout.flush()
        
    def finish(self):
        self.current = self.total
        self._draw()
        print()

def print_status(message, status="INFO", timestamp=True):
    """Print a status message with timestamp and formatting"""
    if timestamp:
        ts = datetime.now().strftime("%H:%M:%S")
        prefix = f"[{ts}]"
    else:
        prefix = ""
    
    if status == "INFO":
        color = "\033[36m"  # Cyan
        symbol = "ℹ"
    elif status == "SUCCESS":
        color = "\033[32m"  # Green
        symbol = "✓"
    elif status == "WARNING":
        color = "\033[33m"  # Yellow
        symbol = "⚠"
    elif status == "ERROR":
        color = "\033[31m"  # Red
        symbol = "✗"
    elif status == "PROCESSING":
        color = "\033[35m"  # Magenta
        symbol = "⚡"
    else:
        color = "\033[0m"   # Reset
        symbol = "•"
    
    reset = "\033[0m"
    print(f"{color}{prefix} {symbol} {message}{reset}")

def print_separator(title=None):
    """Print a separator line with optional title"""
    line = "=" * 60
    if title:
        title_len = len(title)
        if title_len < 56:
            padding = (56 - title_len) // 2
            line = "=" * padding + f" {title} " + "=" * (56 - padding - title_len - 2)
    print(f"\033[34m{line}\033[0m")  # Blue

class SpinnerThread:
    def __init__(self, message):
        self.message = message
        self.running = False
        self.thread = None
        
    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._spin)
        self.thread.daemon = True
        self.thread.start()
        
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
        sys.stdout.write(f"\r{' ' * (len(self.message) + 10)}\r")
        sys.stdout.flush()
        
    def _spin(self):
        spinner_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        i = 0
        while self.running:
            sys.stdout.write(f"\r\033[36m{spinner_chars[i]} {self.message}\033[0m")
            sys.stdout.flush()
            time.sleep(0.1)
            i = (i + 1) % len(spinner_chars)


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



def whisper(path):
    """
    Transcribe audio using Azure OpenAI Whisper, handling large files by splitting if necessary.
    """
    print_status("Starting audio transcription", "PROCESSING")
    max_size_mb = 24  # Azure OpenAI Whisper limit is 24MB per file
    file_size_mb = os.path.getsize(path) / (1024 * 1024)

    if file_size_mb <= max_size_mb:
        spinner = SpinnerThread("Transcribing audio...")
        spinner.start()
        try:
            transcribe = client.audio.transcriptions.create(
                file=open(path, "rb"),
                model="whisper",
                response_format="verbose_json",
                timestamp_granularities=["segment"],
            )
            spinner.stop()
            print_status(f"Transcription completed - {len(transcribe.segments)} segments", "SUCCESS")
            return transcribe
        except Exception as e:
            spinner.stop()
            print_status(f"Transcription failed: {e}", "ERROR")
            raise
    else:
        print_status(f"Large audio file detected ({file_size_mb:.1f}MB), splitting into chunks", "WARNING")
        audio = AudioSegment.from_file(path)
        chunk_length_ms = int((max_size_mb * 1024 * 1024) / (file_size_mb) * len(audio))  # proportional chunk size
        chunk_length_ms = min(chunk_length_ms, 10 * 60 * 1000)  # max 10 min per chunk for safety

        segments = []
        start = 0
        idx = 0
        total_chunks = (len(audio) + chunk_length_ms - 1) // chunk_length_ms
        progress_bar = ProgressBar(total_chunks, "Transcribing chunks")
        
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
            progress_bar.update()

        progress_bar.finish()
        print_status(f"All chunks transcribed - {len(segments)} total segments", "SUCCESS")

        # Compose a result-like object
        class Result:
            def __init__(self, segments):
                self.segments = segments
                self.text = " ".join([seg.text for seg in segments])
                self.duration = segments[-1].end if segments else 0

        return Result(segments)

def tts(text,output_path="./output.mp3"):
    print_status("Starting text-to-speech generation", "PROCESSING")
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
    
    spinner = SpinnerThread("Generating speech audio...")
    spinner.start()
    
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
        
        spinner.stop()
        file_size = os.path.getsize(output_path) / 1024  # KB
        print_status(f"TTS completed - Audio saved ({file_size:.1f}KB)", "SUCCESS")
        return output_path
    except requests.exceptions.RequestException as e:
        spinner.stop()
        print_status(f"TTS failed: {e}", "ERROR")
        return None
    
def gpt_request(messages,text_format=None):
    spinner = SpinnerThread("Processing with AI...")
    spinner.start()
    
    try:
        if text_format is not None:
            response = client.responses.parse(
            model="o4-mini",
            input=messages,
            text_format=text_format,
            )
            spinner.stop()
            print_status("AI processing completed (structured output)", "SUCCESS")
            return response.output_parsed
        else:
            response = client.responses.parse(
            model="o4-mini",
            input=messages,
            )
            spinner.stop()
            print_status("AI processing completed", "SUCCESS")
            return response.output_text
    except Exception as e:
        spinner.stop()
        print_status(f"AI processing failed: {e}", "ERROR")
        return "error"




def video_pipeline(script,output_path):
    print_separator("Video Production Pipeline")
    
    # Step 1: Generate audio
    print_status("Step 1/7: Generating audio", "PROCESSING")
    tts(script,output_path=PATHS["AUDIO_PATH"])

    # Step 2: Create speaker video
    print_status("Step 2/7: Creating speaker video", "PROCESSING")
    spinner = SpinnerThread("Animating speaker...")
    spinner.start()
    make_speaker.create_speaker_video(
        mp3_path=PATHS["AUDIO_PATH"],
        closed_mouth_jpg=PATHS["CLOSE_JPG"],
        open_mouth_jpg=PATHS["OPEN_JPG"],
        output_path=PATHS["BASE_VIDEO"]
    )
    spinner.stop()
    print_status("Speaker video created", "SUCCESS")
    
    # Step 3: Generate SRT
    print_status("Step 3/7: Generating subtitles", "PROCESSING")
    script_timestamps = whisper(PATHS["AUDIO_PATH"])
    script_timestamps = script_timestamps.segments

    srt_processing.generate_srt_file(script_timestamps, output_path=PATHS["SRT"])
    print_status(f"Subtitles generated with {len(script_timestamps)} segments", "SUCCESS")

    # Step 4: Generate video prompts
    print_status("Step 4/7: Generating video prompts", "PROCESSING")
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
    prompt4video = gpt_request(msg,PromptList)
    print_status(f"Generated {len(prompt4video.prompts)} video prompts", "SUCCESS")

    # Step 5: Submit video generation tasks
    print_status("Step 5/7: Submitting video generation tasks", "PROCESSING")
    video_list: list[Video] = []
    task_map = {}
    
    # Submit all video generation tasks and map task_id to video info
    submission_progress = ProgressBar(len(prompt4video.prompts), "Submitting tasks")
    for i, prompt in enumerate(prompt4video.prompts):
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
        submission_progress.update()
        time.sleep(0.5)
    submission_progress.finish()

    # Step 6: Monitor and download videos
    print_status("Step 6/7: Monitoring video generation", "PROCESSING")
    download_progress = ProgressBar(len(task_map), "Downloading videos")
    for task_id, info in task_map.items():
        spinner = SpinnerThread(f"Generating video ({download_progress.current + 1}/{len(task_map)})...")
        spinner.start()
        video_filename = t2v_api_client.monitor_task(task_id)
        spinner.stop()
        
        if not video_filename:
            print_status(f"Failed to generate video for task {task_id}", "ERROR")
            breakpoint()
        
        t2v_api_client.download_video(video_filename, output_path=info["video_path"])
        video_list.append(Video(
            path=info["video_path"],
            start_time=info["start_time"],
            duration=info["duration"]
        ))
        download_progress.update()
    download_progress.finish()

    # Step 7: Final video assembly
    print_status("Step 7/7: Assembling final video", "PROCESSING")
    
    spinner = SpinnerThread("Combining videos...")
    spinner.start()
    video_processing.combine_videos(VIDEO_FPS, PATHS["BASE_VIDEO"], video_list, PATHS["AUDIO_PATH"], PATHS["COMBINED_VIDEO"])
    spinner.stop()
    print_status("Videos combined", "SUCCESS")

    spinner = SpinnerThread("Applying blur effect...")
    spinner.start()
    video_processing.blur_effect(input_path=PATHS["COMBINED_VIDEO"], output_path=PATHS["BLURRED_VIDEO"])
    spinner.stop()
    print_status("Blur effect applied", "SUCCESS")

    spinner = SpinnerThread("Burning subtitles...")
    spinner.start()
    video_processing.burn_subtitle(PATHS["BLURRED_VIDEO"], PATHS["SRT"], output_path=output_path)
    spinner.stop()
    print_status(f"Final video saved: {output_path}", "SUCCESS")

def init():
    """Initialize directories and clean up temporary files"""
    dirs_cleaned = 0
    files_removed = 0
    
    if os.path.exists(PATHS["GENERATED_VIDEOS_DIR"]):
        for filename in os.listdir(PATHS["GENERATED_VIDEOS_DIR"]):
            file_path = os.path.join(PATHS["GENERATED_VIDEOS_DIR"], filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
                files_removed += 1
        dirs_cleaned += 1
    else:
        os.makedirs(PATHS["GENERATED_VIDEOS_DIR"])

    if os.path.exists(PATHS["TEMP_DIR"]):
        for filename in os.listdir(PATHS["TEMP_DIR"]):
            file_path = os.path.join(PATHS["TEMP_DIR"], filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
                files_removed += 1
        dirs_cleaned += 1
    else:
        os.makedirs(PATHS["TEMP_DIR"])
    
    if files_removed > 0:
        print_status(f"Cleaned {files_removed} temporary files from {dirs_cleaned} directories", "INFO")


def main_pipeline(url):
    print_separator("CONTENT PROCESSING PIPELINE")
    
    # Step 1: Download reference video
    print_status("Step 1/4: Downloading reference video", "PROCESSING")
    spinner = SpinnerThread(f"Downloading from {url[:50]}...")
    spinner.start()
    downloader.download_yt(url, output_path=PATHS["REF_AUDIO"])
    spinner.stop()
    print_status("Reference video downloaded", "SUCCESS")

    print_separator()
    
    # Step 2: Transcribe reference video
    print_status("Step 2/4: Transcribing reference video", "PROCESSING")
    ref_text = whisper(PATHS["REF_AUDIO"])
    os.remove(PATHS["REF_AUDIO"])
    ref_text = ref_text.text
    print_status(f"Transcription completed ({len(ref_text)} characters)", "SUCCESS")
    print(f"\033[90m{ref_text[:200]}...\033[0m")  # Show preview in gray

    # Step 3: Clean and process content
    print_separator()
    print_status("Step 3/4: Processing content", "PROCESSING")
    writer_msg = [{"role": "system", "content": content_prompt}, {"role": "user", "content": ref_text}]
    content = gpt_request(writer_msg)
    print_status(f"Content processed ({len(content)} characters)", "SUCCESS")
    print(f"\033[90m{content[:200]}...\033[0m")  # Show preview in gray
    
    print_separator()
    
    # Step 4: Generate short video scripts
    print_status("Step 4/4: Generating short video scripts", "PROCESSING")
    sv_writer_msg = [{"role": "system", "content": sv_prompt}, {"role": "user", "content": content}]
    sv_scripts = gpt_request(sv_writer_msg, ScriptList)
    print_status(f"Generated {len(sv_scripts.scripts)} video scripts", "SUCCESS")

    print_separator("VIDEO PRODUCTION")

    # Video making loop
    details_path = os.path.join(PATHS["FINAL_VIDEOS_DIR"], "video_details.txt")
    uid = uuid4().hex

    with open(details_path, "a", encoding="utf-8") as details_file:
        details_file.write(f"\nSeriesUid: {uid}, Url: {url}\n")

        for index, i in enumerate(sv_scripts.scripts):
            print_separator(f"Video {index + 1}/{len(sv_scripts.scripts)}: {i.title}")
            print_status(f"Script preview: {i.script[:100]}...", "INFO")
            
            output_file = os.path.join(PATHS["FINAL_VIDEOS_DIR"], f"{uid}_{index}.mp4")
            
            start = time.perf_counter()
            video_pipeline(i.script, output_path=output_file)
            elapsed = time.perf_counter() - start
            details_file.write(f"   Video: {index}, Title: {i.title}, FileName: {output_file}, ElapsedSeconds:{elapsed:.2f}\n")
            
            print_status(f"Video {index + 1} completed in {elapsed:.1f}s", "SUCCESS")

    print_separator()
    print_status(f"Series {uid} completed successfully!", "SUCCESS")



def main():
    print_separator("G-MAKER VIDEO GENERATOR")
    print_status("Initializing system...", "PROCESSING")

    if not t2v_api_client.check_health():
        print_status("T2V API is not healthy. Exiting...", "ERROR")
        return

    print_status("T2V API is healthy", "SUCCESS")
    
    # init
    print_status("Cleaning up temporary files...", "PROCESSING")
    init()
    t2v_api_client.clean_queue()
    t2v_api_client.clean_all_video()
    print_status("Cleanup completed", "SUCCESS")
    
    # Ensure directories exist
    for dir_name, dir_path in [
        ("Final videos", PATHS["FINAL_VIDEOS_DIR"]),
        ("Generated videos", PATHS["GENERATED_VIDEOS_DIR"]),
        ("Temporary files", PATHS["TEMP_DIR"])
    ]:
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
            print_status(f"{dir_name} directory created", "INFO")

    print_separator("READY TO PROCESS")

    while True:
        urls = []
        while True:
            print("\n\033[1m🎬 G-Maker Menu:\033[0m")
            print("1. Add a YouTube URL")
            print("2. Add multiple YouTube URLs (comma-separated)")
            print("3. Start processing")
            print("4. Clear output dir")
            print("5. Exit")
            choice = input("\n\033[36mEnter your choice: \033[0m").strip()

            if choice == "1":
                u = input("\033[36mEnter the YouTube URL: \033[0m").strip()
                if u:
                    urls.append(u)
                    print_status(f"Added URL: {u[:50]}...", "SUCCESS")
                else:
                    print_status("No URL entered", "WARNING")
            elif choice == "2":
                s = input("\033[36mEnter URLs separated by commas: \033[0m").strip()
                new_urls = [x.strip() for x in s.split(",") if x.strip()]
                if new_urls:
                    urls.extend(new_urls)
                    print_status(f"Added {len(new_urls)} URLs", "SUCCESS")
                else:
                    print_status("No URLs entered", "WARNING")
            elif choice == "3":
                if not urls:
                    print_status("No URLs provided. Please add at least one URL.", "WARNING")
                    continue
                print_status(f"Starting processing of {len(urls)} URLs...", "PROCESSING")
                break
            elif choice == "4":

                print_status("Clearing output directory...", "PROCESSING")
                files_removed = 0

                if os.path.exists(PATHS["FINAL_VIDEOS_DIR"]):
                    for filename in os.listdir(PATHS["FINAL_VIDEOS_DIR"]):
                        file_path = os.path.join(PATHS["FINAL_VIDEOS_DIR"], filename)
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                            files_removed += 1
                else:
                    os.makedirs(PATHS["FINAL_VIDEOS_DIR"])

                if files_removed > 0:
                    print_status(f"Cleared {files_removed} files from {PATHS['FINAL_VIDEOS_DIR']}", "SUCCESS")

            elif choice == "5":
                print_status("Exiting...", "INFO")
                return
            else:
                print_status("Invalid choice, please try again.", "WARNING")

        # Process URLs
        overall_progress = ProgressBar(len(urls), "Overall progress")
        for idx, url in enumerate(urls):
            try:
                print_separator(f"Processing URL {idx + 1}/{len(urls)}")
                print_status(f"URL: {url}", "INFO")
                main_pipeline(url)
                overall_progress.update()
            except Exception as e:
                print_status(f"Error processing {url}: {e}", "ERROR")
                overall_progress.update()

        overall_progress.finish()
        print_separator("BATCH COMPLETE")
        print_status("All URLs processed successfully!", "SUCCESS")

if __name__ == "__main__":
    main()