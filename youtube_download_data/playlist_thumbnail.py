import os
from pathlib import Path

import yt_dlp

playlist_url = "https://www.youtube.com/playlist?list=PLAg1DP01xg5uh1XNnHo57BWXjKAbsFk5M"
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

ydl_opts = {
    "skip_download": True,
    "writethumbnail": True,
    "playlist_items": "0",
    "outtmpl": str(OUTPUT_DIR / "playlist_thumbnail.%(ext)s"),
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    ydl.download([playlist_url])
