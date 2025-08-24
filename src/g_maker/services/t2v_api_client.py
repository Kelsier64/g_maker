import requests,time
import os
BASE_URL = "http://localhost:8000"

def get_queue_status():
    """Get current queue status"""
    response = requests.get(f"{BASE_URL}/queue/status")
    if response.status_code == 200:
        status = response.json()
        return status
    else:
        return None

def submit_video_generation(prompt, task_name=None, fps=16, num_frames=17, sample_steps=30):
    """Submit a video generation request and return task ID"""
    request_data = {
        "prompt": prompt,
        "negative_prompt": "blurry, low quality, distorted",
        "task": task_name or "t2v-1.3B",
        "size": "480*480",
        "sample_guide_scale": 6.0,
        "sample_steps": sample_steps,
        "num_frames": num_frames,
        "fps": fps,
    }
    
    response = requests.post(f"{BASE_URL}/generate", json=request_data)
    
    if response.status_code == 200:
        result = response.json()
        task_id = result["task_id"]
        return task_id
    elif response.status_code == 503:
        return None
    else:
        return None
    
def download_video(filename, output_path=None):
    """Download a video file"""

    response = requests.get(f"{BASE_URL}/download/{filename}")
    
    if response.status_code == 200:
        local_filename = output_path if output_path else f"downloaded_{filename}"
        dir_name = os.path.dirname(local_filename)
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)
        with open(local_filename, "wb") as f:
            f.write(response.content)
        return True
    else:
        return False

def monitor_task(task_id, poll_interval=10):
    """Monitor a task until completion"""
    
    while True:
        response = requests.get(f"{BASE_URL}/status/{task_id}")
        if response.status_code != 200:
            break
            
        status = response.json()
        status_str = status['status']
        message = status['message']
        
        if status_str == 'completed':
            video_filename = status.get('video_filename')
            return video_filename
        elif status_str == 'failed':
            error = status.get('error', 'Unknown error')
            break
        
        time.sleep(poll_interval)
    
    return None    

def clean_queue():
    """Clean the video generation queue"""
    response = requests.get(f"{BASE_URL}/queue/clean")
    if response.status_code == 200:
        pass
    else:
        pass

def clean_all_video():
    """Clean all video files"""
    response = requests.get(f"{BASE_URL}/videos/clean")
    if response.status_code == 200:
        pass
    else:
        pass

def check_health():
    """Check server health by probing /health endpoint."""
    endpoint = "/health"
    try:
        resp = requests.get(f"{BASE_URL}{endpoint}", timeout=5)
    except requests.RequestException as e:
        return False

    if resp.status_code == 200:
        try:
            body = resp.json()
        except ValueError:
            body = resp.text
        return True
    if resp.status_code == 503:
        return False

    return False

def main():
    task_id = submit_video_generation("A cat playing piano in a cozy jazz club", "test-cat-piano")
    video_filename = monitor_task(task_id)
    if video_filename:
        download_video(video_filename)

if __name__ == "__main__":
    main()