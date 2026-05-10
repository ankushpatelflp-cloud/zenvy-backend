import requests

API_KEY = "YOUR_API_KEY"

def remove_background(image_bytes):
    response = requests.post(
        "https://api.remove.bg/v1.0/removebg",
        files={"image_file": image_bytes},
        data={"size": "auto"},
        headers={"X-Api-Key": API_KEY},
    )

    if response.status_code != 200:
        raise Exception("Background removal failed")

    return response.content