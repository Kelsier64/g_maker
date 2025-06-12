import os,sys
from openai import AzureOpenAI
from dotenv import load_dotenv
from pydantic import BaseModel
load_dotenv()
API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
RESOURCE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")

GPT4O_API_KEY = "2096af94eab44b0bb910def970ad467c"
GPT4O_OPENAI_ENDPOINT = "https://hsh2024.openai.azure.com"

client = AzureOpenAI(
    api_key=API_KEY,
    azure_endpoint=RESOURCE_ENDPOINT,
    api_version="2025-03-01-preview",
    
)

gpt4o_client = AzureOpenAI(
    api_key=GPT4O_API_KEY,
    azure_endpoint=GPT4O_OPENAI_ENDPOINT,
    api_version="2025-03-01-preview",
)

class CalendarEvent(BaseModel):
    name: str
    date: str
    participants: list[str]

def whisper(path):

    transcribe = client.audio.transcriptions.create(
        file=open(path, "rb"),
        model="whisper",
        response_format="verbose_json",
        timestamp_granularities=["segment"],
    )
    return transcribe.segments

def whisper_requests(path,):

    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }
    
    with open(path, "rb") as audio_file:
        files = {
            "file": (os.path.basename(path), audio_file, "audio/mpeg")
        }
        data = {
            "model": "whisper-1",
            "timestamp_granularities[]": "sentence",
            "response_format": "verbose_json",
        }
        
        response = requests.post(
            f"{RESOURCE_ENDPOINT}/openai/deployments/whisper/audio/translations?api-version=2025-03-01-preview",
            headers=headers,
            files=files,
            data=data
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: {response.status_code}, {response.text}")
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

# text = whisper("sound.mp3")
# print(text)

msg =[
    {"role": "system", "content": "Extract the event information."},
    {"role": "user","content": "Alice and Bob are going to a science fair on Friday."}
]
response = gpt4o_request(msg)
print(response)