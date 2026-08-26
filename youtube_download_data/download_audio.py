


from pathlib import Path

import yt_dlp
import os

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


def download_audio( url: str) -> None:
    """Download one YouTube video's audio as ``audio.mp3``."""
    options = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(OUTPUT_DIR, "audio.%(ext)s"),
        "noplaylist": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    }

    with yt_dlp.YoutubeDL(options) as downloader:
        downloader.download([url])


if __name__ == "__main__":
    url = "https://www.youtube.com/watch?v=y62qewQ5qsQ"
    download_audio(url)
    print(f"Downloaded audio to {OUTPUT_DIR / 'audio.mp3'}")
