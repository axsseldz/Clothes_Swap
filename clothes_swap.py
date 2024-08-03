import requests
import uuid
import json
import os
import urllib.parse
from PIL import Image
import io
import websocket

server_address = "vpxd7o5z0fy80a-3020.proxy.runpod.net"
client_id = str(uuid.uuid4())

def queue_prompt(prompt, files):
    payload = {"workflow_id": client_id, "prompt": prompt, "files": files}
    data = json.dumps(payload)
    headers = {'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
    url = f"https://{server_address}/prompt"
    print(f"Sending POST request to {url} with payload:\n{json.dumps(payload, indent=2)}")
    
    response = requests.post(url, data=data, headers=headers)
    if response.status_code != 200:
        print(f"HTTP Error: {response.status_code} - {response.reason}")
        print(f"Response: {response.text}")
        response.raise_for_status()
    return response.json()

def get_image(filename, subfolder, folder_type):
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urllib.parse.urlencode(data)
    headers = {'User-Agent': 'Mozilla/5.0'}
    url = f"https://{server_address}/view?{url_values}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.content

def get_history(prompt_id):
    headers = {'User-Agent': 'Mozilla/5.0'}
    url = f"https://{server_address}/history/{prompt_id}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def get_images(ws, prompt, files):
    prompt_id = queue_prompt(prompt, files)['prompt_id']
    output_images = {}
    while True:
        try:
            out = ws.recv()
            if isinstance(out, str):
                message = json.loads(out)
                if message['type'] == 'executing':
                    data = message['data']
                    if data['node'] is None and data['prompt_id'] == prompt_id:
                        break  # Execution is done
            else:
                continue
        except Exception as e:
            print(f"Error receiving WebSocket message: {e}")
            break

    history = get_history(prompt_id)[prompt_id]
    for o in history['outputs']:
        for node_id in history['outputs']:
            node_output = history['outputs'][node_id]
            if 'images' in node_output:
                images_output = []
                for image in node_output['images']:
                    image_data = get_image(image['filename'], image['subfolder'], image['type'])
                    images_output.append(image_data)
                output_images[node_id] = images_output

    return output_images

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode('utf-8')
        print(f"Encoded image from {image_path}:\n{encoded[:100]}...")  
        return encoded

# Load workflow from file
with open("workflow.json", "r", encoding="utf-8") as f:
    workflow_data = f.read()

prompt = json.loads(workflow_data)

# Load and encode images
person_image_path = "./images/people/rhys.png"
shirt_image_path = "./images/clothes/gucci_white.png"

files = {
    "/input/rhys.png": person_image_path,
    "/input/gucci_white.png": shirt_image_path
}

prompt["1"]["inputs"]["image"] = "rhys.png"
prompt["2"]["inputs"]["image"] = "gucci_white.png"

print("Prompt data being sent:")
print(json.dumps(prompt, indent=2))

# WebSocket connection
ws = websocket.WebSocket()

def process_images():  # FUNCTION TO PROCESS IMAGES - ADDED
    try:
        ws.connect(f"wss://{server_address}/ws?clientId={client_id}")
        images = get_images(ws, prompt, files)
    finally:
        ws.close()

    # Save the output images to the imgs directory:
    os.makedirs("./images/output_imgs", exist_ok=True)
    image_counter = 1
    for node_id in images:
        for image_data in images[node_id]:
            image = Image.open(io.BytesIO(image_data))
            image_path = f"./images/output_imgs/output_image_{image_counter}.png"
            image.save(image_path)
            print(f"Saved image {image_counter} to {image_path}")
            image_counter += 1

# RUN THE PROCESS TWICE - ADDED
process_images()
process_images()
