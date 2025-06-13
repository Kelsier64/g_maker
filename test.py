import asyncio
import os
import httpx  # Replaces 'requests'
import aiofiles # For async file writing

# --- Configuration ---
# Make sure to set these environment variables or replace the placeholders
AZURE_OPENAI_API_KEY = os.environ.get("AZURE_OPENAI_API_KEY", "YOUR_API_KEY_HERE")
AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT", "YOUR_ENDPOINT_HERE")


async def generate_video(
    client: httpx.AsyncClient,  # Pass the client to reuse connections
    prompt: str,
    width: int = 1920,
    height: int = 1080,
    n_seconds: int = 5,
    output_path: str = "output.mp4"
):
    """
    Generates a video based on a prompt using the Azure OpenAI Sora API.
    This function is fully asynchronous.
    """
    api_version = 'preview'
    headers = {
        "api-key": AZURE_OPENAI_API_KEY,
        "Content-Type": "application/json"
    }
    print(f"[{prompt[:20]}...] Starting job...")

    # 1. Create a video generation job (asynchronous)
    create_url = f"{AZURE_OPENAI_ENDPOINT}/openai/v1/video/generations/jobs?api-version={api_version}"
    body = {
        "prompt": prompt,
        "width": width,
        "height": height,
        "n_seconds": n_seconds,
        "model": "sora"
    }
    # Use 'await' with the async client
    response = await client.post(create_url, headers=headers, json=body)
    response.raise_for_status()
    job_id = response.json()["id"]
    print(f"[{prompt[:20]}...] Job created: {job_id}")

    # 2. Poll for job status (asynchronous)
    status_url = f"{AZURE_OPENAI_ENDPOINT}/openai/v1/video/generations/jobs/{job_id}?api-version={api_version}"
    status = None
    while status not in ("succeeded", "failed", "cancelled"):
        # Use 'asyncio.sleep' instead of 'time.sleep'
        await asyncio.sleep(5)
        status_response = await client.get(status_url, headers=headers)
        status_response.raise_for_status()
        status_data = status_response.json()
        status = status_data.get("status")
        print(f"[{prompt[:20]}...] Job status: {status}")

    # 3. Retrieve generated video (asynchronous)
    if status == "succeeded":
        generations = status_data.get("generations", [])
        if generations:
            print(f"✅ [{prompt[:20]}...] Video generation succeeded.")
            generation_id = generations[0].get("id")
            video_url = f"{AZURE_OPENAI_ENDPOINT}/openai/v1/video/generations/{generation_id}/content/video?api-version={api_version}"
            
            # Use the async client to download the video content
            video_response = await client.get(video_url, headers=headers)
            video_response.raise_for_status()
            
            # Ensure output directory exists
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
                
            # Use aiofiles to write the file asynchronously
            async with aiofiles.open(output_path, "wb") as file:
                await file.write(video_response.content)
                
            print(f'✅ [{prompt[:20]}...] Generated video saved as "{output_path}"')
            return output_path
        else:
            raise Exception(f"[{prompt[:20]}...] No generations found in job result.")
    else:
        raise Exception(f"[{prompt[:20]}...] Job failed. Status: {status}")


async def main():
    """
    Main function to run multiple video generation tasks concurrently.
    """
    # Use an async context manager for the client to handle setup/teardown
    async with httpx.AsyncClient(timeout=None) as client:
        # Create a list of tasks (coroutines) to run
        tasks = [
            generate_video(
                client,
                "A sweeping aerial shot of a vast mountain range at sunrise, with golden light casting long shadows over the rugged peaks.",
                n_seconds=2,
                output_path="output/mountains.mp4"
            ),
            generate_video(
                client,
                "A stylish woman walks down a Tokyo street filled with warm glowing neon and animated city signage.",
                n_seconds=2,
                output_path="output/tokyo_street.mp4"
            )
        ]

        # asyncio.gather runs all tasks concurrently and waits for them all to finish
        print("--- Starting all video generation tasks concurrently ---")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        print("\n--- All tasks have completed ---")

        # Process the results
        for result in results:
            if isinstance(result, Exception):
                print(f"A task failed: {result}")
            else:
                print(f"Successfully completed: {result}")


if __name__ == "__main__":
    # This is how you run the top-level async function
    asyncio.run(main())