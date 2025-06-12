import os,sys
from openai import AzureOpenAI
from dotenv import load_dotenv
import requests
import yt_dlp
import json
from pydantic import BaseModel
load_dotenv()
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")

GPT4O_API_KEY = "2096af94eab44b0bb910def970ad467c"
GPT4O_OPENAI_ENDPOINT = "https://hsh2024.openai.azure.com"
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"


# cotent bg_video bgm 


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


def download_yt(url, format_type="mp3"):
    """
    Download YouTube video as mp3 or mp4
    
    Args:
        url: YouTube URL
        format_type: "mp3" or "mp4"
    """
    # Define fixed output paths based on format type
    output_path = "./sound.mp3" if format_type == "mp3" else "./video.mp4"
    
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


test_config = {
    "content_url": "https://youtu.be/dQw4w9WgXcQ",
    "bgv_url": "https://youtu.be/dQw4w9WgXcQ",
    "bgm_url": "https://youtu.be/dQw4w9WgXcQ"
}


def main(url="https://youtu.be/dQw4w9WgXcQ"):
    # download_yt(url)
    # ref_text = whisper("sound.mp3")
    # ref_text = ref_text.text
    # print(ref_text)
    # writer_prompt = [{"role":"system","content":"rewrite the reference text as a spoken script for a youtube video,only output the script dont say other thing"},{"role":"user","content":ref_text}]
    # script = gpt4o_request(writer_prompt)
    # print(script)  
    script = test_script

    # tts(script)
    script_timestamps = whisper("output.mp3")
    script_timestamps = script_timestamps.segments

    script_for_ai = []
    for segment in script_timestamps:
        script_for_ai.append({
            "start": round(segment.start,1),
            "end": round(segment.end,1),
            "text": segment.text.strip()
        })
    print(script_for_ai)
    


    # tts("Hello, this is a test.")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        url = sys.argv[1]
        main(url)
        
    else:
        main()