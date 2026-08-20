"""Download an ``audio.mp3`` file for every Zoe Languages lesson.

Each lesson folder must contain ``description.json`` with a ``youtube_id``.
Run from the repository root:

    python process_youtube/download_audio.py
"""

import json
from pathlib import Path

import yt_dlp


PROJECT_ROOT = Path(__file__).resolve().parent.parent
LESSONS_PATH = PROJECT_ROOT / "youtube_data" / "zoe_languages" / "lessons"


def download_audio(lesson_path: Path, youtube_id: str) -> None:
    """Download one YouTube video's audio as ``audio.mp3``."""
    options = {
        "format": "bestaudio/best",
        "outtmpl": str(lesson_path / "audio.%(ext)s"),
        "noplaylist": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    }
    url = f"https://www.youtube.com/watch?v={youtube_id}"
    with yt_dlp.YoutubeDL(options) as downloader:
        downloader.download([url])


def main() -> None:
    failures = 0
    description_paths = sorted(LESSONS_PATH.glob("*/description.json"))

    for description_path in description_paths:
        lesson_path = description_path.parent
        audio_path = lesson_path / "audio.mp3"
        if audio_path.exists():
            print(f"{lesson_path.name}: skipped (audio.mp3 already exists)")
            continue

        try:
            metadata = json.loads(description_path.read_text(encoding="utf-8"))
            youtube_id = metadata["youtube_id"]
            if not isinstance(youtube_id, str) or len(youtube_id) != 11:
                raise ValueError("youtube_id must be an 11-character string")
            download_audio(lesson_path, youtube_id)
        except (KeyError, ValueError, json.JSONDecodeError, yt_dlp.utils.DownloadError) as error:
            failures += 1
            print(f"{lesson_path.name}: failed ({error})")
        else:
            print(f"{lesson_path.name}: downloaded")

    print(f"\\nProcessed {len(description_paths)} lessons; {failures} failed.")


if __name__ == "__main__":
    main()
