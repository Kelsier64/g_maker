from openai import OpenAI
import base64,os
from dotenv import load_dotenv
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=API_KEY) 

def generate_image(prompt,output_path="image.jpg"):

    result = client.images.generate(
        model="gpt-image-1",
        size="1024x1024",
        quality="low",
        prompt=prompt
    )

    # Decode the generated image
    image_base64 = result.data[0].b64_json
    image_bytes = base64.b64decode(image_base64)
    
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    with open(output_path, "wb") as f:
        f.write(image_bytes)


generate_image("A beautiful landscape with mountains and a river"  )

