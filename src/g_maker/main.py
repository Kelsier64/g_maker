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




def video_pipeline(script,output_path):

    print("Generating audio...")
    tts(script,output_path=PATHS["AUDIO_PATH"])

    make_speaker.create_speaker_video(
        mp3_path=PATHS["AUDIO_PATH"],
        closed_mouth_jpg=PATHS["CLOSE_JPG"],
        open_mouth_jpg=PATHS["OPEN_JPG"],
        output_path=PATHS["BASE_VIDEO"]
    )
    print("Generating srt...")
    script_timestamps = whisper(PATHS["AUDIO_PATH"])
    script_timestamps = script_timestamps.segments

    srt_processing.generate_srt_file(script_timestamps, output_path=PATHS["SRT"])

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
    video_processing.combine_videos(VIDEO_FPS, PATHS["BASE_VIDEO"], video_list, PATHS["AUDIO_PATH"], PATHS["COMBINED_VIDEO"])

    print("Applying blur effect to video...")
    video_processing.blur_effect(input_path=PATHS["COMBINED_VIDEO"], output_path=PATHS["BLURRED_VIDEO"])

    print("Burning subtitles into video...")
    video_processing.burn_subtitle(PATHS["BLURRED_VIDEO"], PATHS["SRT"], output_path=output_path)






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


def main_pipeline(url):
    print(f"Downloading reference video from {url}...")
    downloader.download_yt(url, output_path=PATHS["REF_AUDIO"])

    print("\n")
    print("="*20)
    print("\n")
    print("Transcribing reference video...")
    ref_text = whisper(PATHS["REF_AUDIO"])
    os.remove(PATHS["REF_AUDIO"])
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

    if not os.path.exists(PATHS["FINAL_VIDEOS_DIR"]):
        os.makedirs(PATHS["FINAL_VIDEOS_DIR"], exist_ok=True)
    details_path = os.path.join(PATHS["FINAL_VIDEOS_DIR"], "video_details.txt")
    
    uid = uuid4().hex
    with open(details_path, "w", encoding="utf-8") as details_file:
        details_file.write(f"SourceUid: {uid}, Url: {url}\n")

        for index, i in enumerate(sv_scripts.scripts):
            
            print(f"Title: {i.title}, Script: {i.script}")
            print("="*20)
            init()

            output_file = os.path.join(PATHS["FINAL_VIDEOS_DIR"], f"{uid}_{index}.mp4")
            
            start = time.perf_counter()
            video_pipeline(i.script, output_path=output_file)
            elapsed = time.perf_counter() - start
            details_file.write(f"   Video: {index}, Title: {i.title}, FileName: {output_file}, ElapsedSeconds:{elapsed:.2f}\n")

    print(f"\nseries {uid} done")



def main():

    if not t2v_api_client.check_health():
        print("❌ T2V API is not healthy. Exiting...")
        return

    # init
    init()
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
                main_pipeline(url)
            except Exception as e:
                print(f"Error processing {url}: {e}")

        print("All done.")

if __name__ == "__main__":
    main()