import requests
import json
import time
import io
import sys
from g_maker.config import COMFY_ADDRESS,PATHS

def free_memory():
    free_api_url = f"http://{COMFY_ADDRESS}/free"
    payload = {"unload_models": True, "free_memory": True}
    try:
        response = requests.post(free_api_url, json=payload)
        response.raise_for_status() 
        return response.status_code
    except requests.exceptions.RequestException as e:
        print(f"Error freeing memory: {e}")
        return None

def generate_video(width=None, height=None, num_frames=None, positive_prompt=None, negative_prompt=None, output_path=None):

    workflow_file_path = PATHS['WORKFLOW_PATH']
    
    with open(workflow_file_path, 'r', encoding='utf-8') as f:
        workflow_data = json.load(f)

    # Modify video parameters if provided
    if width is not None or height is not None or num_frames is not None:
        # Find node 98 (WanVideoEmptyEmbeds) and update parameters
        if "98" in workflow_data:
            if width is not None:
                workflow_data["98"]["inputs"]["width"] = width
                # print(f"Updated width to: {width}")
            if height is not None:
                workflow_data["98"]["inputs"]["height"] = height
                # print(f"Updated height to: {height}")
            if num_frames is not None:
                workflow_data["98"]["inputs"]["num_frames"] = num_frames
                # print(f"Updated num_frames to: {num_frames}")
        else:
            print("Warning: Node 98 (WanVideoEmptyEmbeds) not found in workflow")

    # Modify prompt text if provided
    if positive_prompt is not None or negative_prompt is not None:
        # Find node 16 (WanVideoTextEncode) and update prompts
        if "16" in workflow_data:
            if positive_prompt is not None:
                workflow_data["16"]["inputs"]["positive_prompt"] = positive_prompt
                # print(f"Updated positive prompt to: {positive_prompt[:50]}...")
            if negative_prompt is not None:
                workflow_data["16"]["inputs"]["negative_prompt"] = negative_prompt
                # print(f"Updated negative prompt to: {negative_prompt[:50]}...")
        else:
            print("Warning: Node 16 (WanVideoTextEncode) not found in workflow")

    prompt_api_url = f"http://{COMFY_ADDRESS}/prompt"

    payload = {
        "prompt": workflow_data, 
    }
    try:
        response = requests.post(prompt_api_url, json=payload)
        response.raise_for_status() 
        result = response.json()
       
        prompt_id = result['prompt_id']
        # print(f"ID: {prompt_id}")
    except requests.exceptions.RequestException as e:
        print(f"{e}")
        sys.exit(1)


    history_api_url = f"http://{COMFY_ADDRESS}/history"


    # print("waiting...", end='')
    while True:
        time.sleep(1) 

        response = requests.get(history_api_url)
        history = response.json()
        
        if prompt_id in history:
            result_data = history[prompt_id]
            outputs = result_data.get('outputs', {})

            for node_id, node_output in outputs.items():
                if 'gifs' in node_output:
                    for gif_info in node_output['gifs']:
                        gif_filename = gif_info['filename']
                        gif_url = f"http://{COMFY_ADDRESS}/view?filename={gif_filename}&subfolder={gif_info.get('subfolder', '')}&type={gif_info.get('type', 'output')}"
                        gif_response = requests.get(gif_url)
                        # Save video to local file
                        if output_path is None:
                            output_path = f"{PATHS['GENERATED_VIDEOS_DIR']}/{gif_filename}"
                        with open(output_path, 'wb') as f:
                            f.write(gif_response.content)
                        # Only save the first gif and return its path
                        return output_path
            # If prompt_id found but no gifs yet, keep waiting


if __name__ == "__main__":
    path = generate_video(height=720, width=720, num_frames=33, positive_prompt="nude anime girl showing here nipples")
    path = generate_video(height=720, width=720, num_frames=129, positive_prompt="nude anime girl with firm tits")
    path = generate_video(height=720, width=720, num_frames=33, positive_prompt="nude anime girl with uplifted tits")
    print(f"Video saved to: {path}")