import json
from pathlib import Path

import yt_dlp

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LESSONS_PATH = PROJECT_ROOT / "youtube_data" / "short story for learning english" / 'lessons'
# C:\Users\PC\Desktop\whisper\youtube_data\short story for learning english

def download_audio(lesson_path: Path, youtube_id: str) -> None:
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

    for lesson_path in sorted(LESSONS_PATH.iterdir()):
        if not lesson_path.is_dir():
            continue

        description_path = lesson_path / "description.json"
        audio_path = lesson_path / "audio.mp3"

        if audio_path.exists():
            print(f"{lesson_path.name}: skipped — audio.mp3 already exists")
            continue

        if not description_path.exists():
            print(f"{lesson_path.name}: no description.json")
            continue

        try:
            description = json.loads(description_path.read_text(encoding="utf-8"))
            youtube_id = description.get("youtube_id")

            if not isinstance(youtube_id, str) or len(youtube_id) != 11:
                raise ValueError("youtube_id is missing or invalid")

            download_audio(lesson_path, youtube_id)
            print(f"{lesson_path.name}: downloaded")

        except Exception as error:
            failures += 1
            print(f"{lesson_path.name}: failed — {error}")

    print(f"\nFinished. Failed downloads: {failures}")


if __name__ == "__main__":
    main()