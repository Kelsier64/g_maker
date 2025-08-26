import os
import time
import tempfile
import threading
import sys
from openai import AzureOpenAI, OpenAI
from pydub import AudioSegment
from dotenv import load_dotenv

from g_maker.utils.terminal import print_status, ProgressBar, SpinnerThread

load_dotenv()

# AI API Keys and Endpoints
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
GPT4O_API_KEY = "2096af94eab44b0bb910def970ad467c"
GPT4O_OPENAI_ENDPOINT = "https://hsh2024.openai.azure.com"
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Voice and processing settings
VOICE_ID = "MFZUKuGQUsGJPQjTS4wC"
WHISPER_MODE = "segment"



# AI Clients
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

# Utility classes for terminal output
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
                timestamp_granularities=[WHISPER_MODE],
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


def tts(text, output_path="./output.mp3"):
    from ..utils.terminal import print_status, SpinnerThread
    import requests
    
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

def gpt_request(messages, text_format=None):
    from ..utils.terminal import print_status, SpinnerThread
    
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
