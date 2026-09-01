"""Download every accessible episode from a Bilibili playlist as MP3 files.

Only download material you own or are authorized to save.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import yt_dlp


DEFAULT_PLAYLIST_URL = "https://www.bilibili.com/video/BV1434y1d7cX"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "bilibili"


def download_playlist(playlist_url: str, output_dir: Path) -> int:
    """Download a Bilibili playlist and convert each available item to MP3."""
    output_dir.mkdir(parents=True, exist_ok=True)

    ydl_options = {
        "format": "bestaudio/best",
        "outtmpl": str(output_dir / "%(playlist_index)03d - %(title)s.%(ext)s"),
        "noplaylist": False,
        "ignoreerrors": True,
        "continuedl": True,
        "overwrites": False,
        "retries": 10,
        "fragment_retries": 10,
        "windowsfilenames": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    }

    with yt_dlp.YoutubeDL(ydl_options) as ydl:
        return ydl.download([playlist_url])


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download all accessible audio from a Bilibili playlist as MP3."
    )
    parser.add_argument(
        "url",
        nargs="?",
        default=DEFAULT_PLAYLIST_URL,
        help="Bilibili playlist or video URL",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Folder where MP3 files will be saved",
    )
    args = parser.parse_args()

    print(f"Saving audio to: {args.output.resolve()}")
    exit_code = download_playlist(args.url, args.output)
    if exit_code:
        raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
