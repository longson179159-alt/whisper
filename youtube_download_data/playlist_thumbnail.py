import os
from pathlib import Path

import yt_dlp

playlist_url = "https://www.youtube.com/playlist?list=PLphcdvnT8lOuG5CZp9sj4QYuuXQNi_-WK"
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

ydl_opts = {
    "skip_download": True,
    "writethumbnail": True,
    "playlist_items": "0",
    "outtmpl": os.path.join(OUTPUT_DIR, "image.%(ext)s"),
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    ydl.download([playlist_url])
