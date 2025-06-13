import requests
import base64 
import os
from dotenv import load_dotenv
import time
# Set environment variables or edit the corresponding values here.
load_dotenv()
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")

def generate_video(prompt, width=480, height=480, n_seconds=5, output_path="output.mp4"):
    api_version = 'preview'
    headers = {
        "api-key": AZURE_OPENAI_API_KEY,
        "Content-Type": "application/json"
    }

    # 1. Create a video generation job
    create_url = f"{AZURE_OPENAI_ENDPOINT}/openai/v1/video/generations/jobs?api-version={api_version}"
    body = {
        "prompt": prompt,
        "width": width,
        "height": height,
        "n_seconds": n_seconds,
        "model": "sora"
    }
    response = requests.post(create_url, headers=headers, json=body)
    response.raise_for_status()
    job_id = response.json()["id"]
    print(f"Job created: {job_id}")

    # 2. Poll for job status
    status_url = f"{AZURE_OPENAI_ENDPOINT}/openai/v1/video/generations/jobs/{job_id}?api-version={api_version}"
    status = None
    while status not in ("succeeded", "failed", "cancelled"):
        time.sleep(5)
        status_response = requests.get(status_url, headers=headers).json()
        status = status_response.get("status")
        print(f"Job status: {status}")

    # 3. Retrieve generated video 
    if status == "succeeded":
        generations = status_response.get("generations", [])
        if generations:
            print(f"✅ Video generation succeeded.")
            generation_id = generations[0].get("id")
            video_url = f"{AZURE_OPENAI_ENDPOINT}/openai/v1/video/generations/{generation_id}/content/video?api-version={api_version}"
            video_response = requests.get(video_url, headers=headers)
            if video_response.ok:
                # Ensure output directory exists
                os.makedirs(os.path.dirname(output_path), exist_ok=True) if os.path.dirname(output_path) else None
                with open(output_path, "wb") as file:
                    file.write(video_response.content)
                print(f'Generated video saved as "{output_path}"')
                return output_path
            else:
                raise Exception("Failed to download video content.")
        else:
            raise Exception("No generations found in job result.")
    else:
        raise Exception(f"Job didn't succeed. Status: {status}")

# Example usage:
generate_video("")