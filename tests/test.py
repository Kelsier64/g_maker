import requests

def free_memory():
    server_address = 'localhost:8188'
    free_api_url = f"http://{server_address}/free"
    payload = {"unload_models": True, "free_memory": True}
    try:
        response = requests.post(free_api_url, json=payload)
        response.raise_for_status() 
        return response.status_code
    except requests.exceptions.RequestException as e:
        print(f"Error freeing memory: {e}")
        return None

free_memory()