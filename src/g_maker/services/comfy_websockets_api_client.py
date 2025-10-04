import websocket #NOTE: websocket-client (https://github.com/websocket-client/websocket-client)
import uuid
import json
import urllib.request
import urllib.parse
import sys
import requests
import time
from g_maker.config import PATHS

def queue_prompt(prompt, server_address, client_id):
    p = {"prompt": prompt, "client_id": client_id}
    data = json.dumps(p).encode('utf-8')
    req =  urllib.request.Request("http://{}/prompt".format(server_address), data=data)
    return json.loads(urllib.request.urlopen(req).read())

def get_history(prompt_id, server_address):
    with urllib.request.urlopen("http://{}/history/{}".format(server_address, prompt_id)) as response:
        return json.loads(response.read())

def get_image(prompt, server_address, client_id, output_path=None):
    # Queue prompt using client_id (keeping original approach)
    prompt_id = queue_prompt(prompt, server_address, client_id)['prompt_id']
    
    # Poll history until completion (comfy_api_client approach)
    history_api_url = f"http://{server_address}/history"
    
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
                        gif_url = f"http://{server_address}/view?filename={gif_filename}&subfolder={gif_info.get('subfolder', '')}&type={gif_info.get('type', 'output')}"
                        gif_response = requests.get(gif_url)
                        # Save video to local file
                        if output_path is None:
                            output_path = f"{PATHS['GENERATED_VIDEOS_DIR']}/{gif_filename}"
                        with open(output_path, 'wb') as f:
                            f.write(gif_response.content)
                        # Only save the first gif and return its path
                        return output_path
            # If prompt_id found but no gifs yet, keep waiting


def generate_video(client_id=None,width=None, height=None, positive_prompt=None, negative_prompt=None, num_frames=None, output_path=None):
   
    server_address = PATHS['COMFY_ADDRESS']
    workflow_file_path = PATHS['WORJFLOW_PATH']
    if client_id is None:
        client_id = str(uuid.uuid4())
    
    # Load workflow from JSON file (same as comfy_api_client)
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
    
    try:
        # Use HTTP polling approach but keep client_id for prompt submission
        result_path = get_image(workflow_data, server_address, client_id, output_path)
        
        if result_path:
            return result_path
        else:
            print("Warning: No videos were generated")
            return None
        
    except Exception as e:
        print(f"Error generating video: {e}")
        sys.exit(1)


if __name__ == "__main__":
    id = str(uuid.uuid4())
    path = generate_video(
        client_id=id,
        width=720, 
        height=720, 
        positive_prompt="nude anime girl with firm breasts",
        num_frames=33
    )
    path = generate_video(
        client_id=id,
        width=720, 
        height=720, 
        positive_prompt="nude anime girl with uplifted breasts", #perky breasts
        num_frames=40
    )

