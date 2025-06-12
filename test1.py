import os,sys
from openai import AzureOpenAI
from dotenv import load_dotenv
from pydantic import BaseModel
load_dotenv()
API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
RESOURCE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")

GPT4O_API_KEY = "2096af94eab44b0bb910def970ad467c"
GPT4O_OPENAI_ENDPOINT = "https://hsh2024.openai.azure.com"

data=[{'start': 0.0, 'end': 2.6, 'text': 'Hey, did you know the Great Pyramid of Giza'}, {'start': 2.6, 'end': 7.0, 'text': 'was the tallest structure on Earth for over 3,800 years,'}, {'start': 7.0, 'end': 12.2, 'text': 'built without modern machines, just manpower, math and mystery?'}, {'start': 12.2, 'end': 13.4, 'text': "Let's dive in."}, {'start': 13.4, 'end': 16.4, 'text': 'The pyramids of Egypt, especially the Great Pyramid,'}, {'start': 16.4, 'end': 19.5, 'text': 'are one of the seven wonders of the ancient world.'}, {'start': 19.5, 'end': 24.0, 'text': 'Built over 4,500 years ago during the reign of Pharaoh Khufu,'}, {'start': 24.0, 'end': 29.4, 'text': 'this massive stone structure originally stood 146 meters tall.'}, {'start': 29.4, 'end': 31.9, 'text': "That's roughly a 45-story building."}, {'start': 31.9, 'end': 35.5, 'text': "It's made from over 2 million limestone and granite blocks."}, {'start': 35.5, 'end': 38.3, 'text': 'Each block can weigh up to 80 tons.'}, {'start': 38.3, 'end': 40.0, 'text': "And here's the wild part."}, {'start': 40.0, 'end': 44.5, 'text': "We still don't fully understand how they moved and stacked them so precisely."}, {'start': 44.5, 'end': 46.4, 'text': "So how'd they build it?"}, {'start': 46.4, 'end': 47.8, 'text': 'There are a few theories.'}, {'start': 47.8, 'end': 49.6, 'text': 'First, the ramp theory.'}, {'start': 49.6, 'end': 53.4, 'text': 'Maybe they used long ramps made of mud brick and limestone.'}, {'start': 53.4, 'end': 55.4, 'text': 'Second, the spiral theory.'}, {'start': 55.4, 'end': 59.0, 'text': 'Some think ramps spiraled around the pyramid as it rose.'}, {'start': 59.0, 'end': 61.6, 'text': 'And third, the internal spiral theory.'}, {'start': 61.6, 'end': 64.3, 'text': 'A newer idea that suggests a hidden inner ramp'}, {'start': 64.3, 'end': 67.2, 'text': 'helped workers build it from the inside out.'}, {'start': 67.2, 'end': 72.0, 'text': 'Still no solid proof for any of them, which makes it even more fascinating.'}, {'start': 72.0, 'end': 76.1, 'text': 'In 2017, scientists discovered a mysterious hidden void'}, {'start': 76.1, 'end': 79.9, 'text': 'inside the Great Pyramid using cosmic ray technology.'}, {'start': 79.9, 'end': 81.8, 'text': "No one knows what's in it."}, {'start': 81.8, 'end': 83.2, 'text': 'Yet.'}, {'start': 83.2, 'end': 86.4, 'text': 'Also, the alignment of the pyramid is insanely accurate.'}, {'start': 86.5, 'end': 91.0, 'text': "It's almost perfectly aligned with true north, south, east, and west."}, {'start': 91.0, 'end': 94.1, 'text': 'With less than 0.05 degrees of error.'}, {'start': 94.1, 'end': 96.5, 'text': 'Try doing that without GPS.'}, {'start': 96.5, 'end': 97.6, 'text': 'Quick facts.'}, {'start': 97.6, 'end': 100.7, 'text': 'The pyramid was originally covered in polished white limestone'}, {'start': 100.7, 'end': 103.1, 'text': 'that reflected the sun like a mirror.'}, {'start': 103.1, 'end': 104.7, 'text': "The builders weren't slaves."}, {'start': 104.7, 'end': 108.3, 'text': 'They were skilled laborers, well-fed and respected.'}, {'start': 108.3, 'end': 112.3, 'text': "Some believe the pyramid's proportions match the golden ratio."}, {'start': 112.3, 'end': 114.7, 'text': 'Coincidence or design?'}, {'start': 114.7, 'end': 117.9, 'text': "Whether it's math, mystery, or just pure human genius,"}, {'start': 117.9, 'end': 121.6, 'text': 'the pyramids remain one of the greatest achievements in history.'}, {'start': 121.6, 'end': 123.1, 'text': 'If you learned something new,'}, {'start': 123.1, 'end': 126.2, 'text': 'hit like and follow for more history in under three minutes.'}]

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


class Prompt(BaseModel):
    prompt: str
    start_time: float
    seconds: int


class PromptList(BaseModel):
    prompts: list[Prompt]

    def __str__(self):
        return "\n".join(self.prompts)

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
    {"role": "system", "content": "generate some video generating prompts for the following text, each prompt should be a dictionary with keys: 'prompt', 'start_time', and 'seconds'. The 'prompt' should be a detailed description of the video you want to generate, 'start_time' is the start time in seconds, and 'seconds' is the duration in seconds."},
    {"role": "user","content": data.__str__()}
]
response = gpt4o_request(msg,PromptList)
for i in response.prompts:
    print(f"Prompt: {i.prompt}, Start Time: {i.start_time}, Duration: {i.seconds} seconds")