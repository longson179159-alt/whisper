import requests
import re
import json
import os

channel_url = "https://www.youtube.com/@BuddhismInEnglish"
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

headers = {
    "User-Agent": "Mozilla/5.0"
}

html = requests.get(channel_url, headers=headers).text

match = re.search(r'"avatar":\{"thumbnails":(\[.*?\])\}', html)

if match:
    thumbnails = json.loads(match.group(1))

    # Usually the last one is the largest
    avatar_url = thumbnails[-1]["url"]

    print("Avatar URL:")
    print(avatar_url)

    image = requests.get(avatar_url, headers=headers)
    image.raise_for_status()

    # avatar_path = OUTPUT_DIR / "avatar.jpg"
    avatar_path = os.path.join(OUTPUT_DIR, "avatar.jpg")
    with open(avatar_path, "wb") as f:
        f.write(image.content)

    print(f"Saved: {avatar_path}")
else:
    print("Avatar not found")
