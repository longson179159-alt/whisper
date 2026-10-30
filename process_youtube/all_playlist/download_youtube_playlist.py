"""Build a course from the YouTube URLs listed in ``peding.txt``.

Each URL becomes a numbered lesson folder containing an MP3, a JPG thumbnail,
and a plain-text English transcript. If English captions are unavailable, the
transcript file is created empty.
"""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

import yt_dlp
from yt_dlp.utils import DownloadError


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_URL_FILE = SCRIPT_DIR / "peding.txt"
DEFAULT_OUTPUT_DIR = SCRIPT_DIR.parents[1] / "en" / "To fluency" / "LESSONS"

INVALID_WINDOWS_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
VTT_TAG = re.compile(r"<[^>]+>")


def read_urls(url_file: Path) -> list[str]:
    """Return non-empty, non-comment URL lines in their original order."""
    return [
        line.strip()
        for line in url_file.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def safe_title(title: str, max_length: int = 120) -> str:
    """Make a readable title safe for a Windows folder and filenames."""
    title = INVALID_WINDOWS_CHARS.sub("", html.unescape(title))
    title = re.sub(r"\s+", " ", title).strip().rstrip(".")
    return title[:max_length].rstrip(" .") or "Untitled lesson"


def english_subtitle_language(info: dict) -> str | None:
    """Prefer manual English captions, then fall back to automatic captions."""
    for source_name in ("subtitles", "automatic_captions"):
        languages = info.get(source_name) or {}
        english = [
            language
            for language in languages
            if language.lower() == "en" or language.lower().startswith("en-")
        ]
        if english:
            return sorted(english, key=lambda language: (language != "en", language))[0]
    return None


def vtt_to_text(vtt_path: Path) -> str:
    """Convert WebVTT captions into simple readable text."""
    output_lines: list[str] = []
    in_note = False

    for raw_line in vtt_path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        line = raw_line.strip()

        if line.startswith("NOTE"):
            in_note = True
            continue
        if in_note:
            if not line:
                in_note = False
            continue
        if (
            not line
            or line == "WEBVTT"
            or line.startswith(("Kind:", "Language:", "STYLE", "REGION"))
            or "-->" in line
            or line.isdigit()
        ):
            continue

        line = html.unescape(VTT_TAG.sub("", line)).strip()
        if line and (not output_lines or line != output_lines[-1]):
            output_lines.append(line)

    return "\n".join(output_lines) + ("\n" if output_lines else "")


def metadata_options() -> dict:
    return {
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "js_runtimes": {"node": {}},
    }


def download_options(lesson_dir: Path, base_name: str, subtitle_language: str | None) -> dict:
    options = {
        "format": "bestaudio/best",
        "outtmpl": str(lesson_dir / f"{base_name}.%(ext)s"),
        "noplaylist": True,
        "continuedl": True,
        "overwrites": False,
        "windowsfilenames": True,
        "writethumbnail": True,
        "js_runtimes": {"node": {}},
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            },
            {
                "key": "FFmpegThumbnailsConvertor",
                "format": "jpg",
            },
        ],
    }

    if subtitle_language:
        options.update(
            {
                "writesubtitles": True,
                "writeautomaticsub": True,
                "subtitleslangs": [subtitle_language],
                "subtitlesformat": "vtt",
            }
        )

    return options


def download_lesson(index: int, url: str, output_dir: Path) -> None:
    """Download one lesson and create its plain-text subtitle file."""
    with yt_dlp.YoutubeDL(metadata_options()) as ydl:
        info = ydl.extract_info(url, download=False)

    title = safe_title(info.get("title") or info.get("id") or "Untitled lesson")
    base_name = f"{index}. {title}"
    lesson_dir = output_dir / base_name
    lesson_dir.mkdir(parents=True, exist_ok=True)

    subtitle_language = english_subtitle_language(info)
    print(f"[{index}] {title}")
    print(f"    English subtitles: {subtitle_language or 'not available (blank TXT)'}")

    with yt_dlp.YoutubeDL(
        download_options(lesson_dir, base_name, subtitle_language)
    ) as ydl:
        ydl.download([url])

    transcript_path = lesson_dir / f"{base_name}.txt"
    subtitle_files = sorted(lesson_dir.glob(f"{base_name}.*.vtt"))
    transcript = vtt_to_text(subtitle_files[0]) if subtitle_files else ""
    transcript_path.write_text(transcript, encoding="utf-8")

    for subtitle_file in subtitle_files:
        subtitle_file.unlink()


def build_course(url_file: Path, output_dir: Path) -> None:
    urls = read_urls(url_file)
    if not urls:
        raise ValueError(f"No URLs found in {url_file}")

    output_dir.mkdir(parents=True, exist_ok=True)
    failures: list[tuple[int, str]] = []

    for index, url in enumerate(urls, start=1):
        try:
            download_lesson(index, url, output_dir)
        except DownloadError as error:
            failures.append((index, url))
            print(f"[{index}] Download failed: {error}")

    print(f"\nFinished: {len(urls) - len(failures)}/{len(urls)} lessons downloaded")
    print(f"Course folder: {output_dir.resolve()}")
    if failures:
        print("Failed URLs:")
        for index, url in failures:
            print(f"  {index}. {url}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a numbered MP3/JPG/TXT course from YouTube URLs."
    )
    parser.add_argument(
        "--urls",
        type=Path,
        default=DEFAULT_URL_FILE,
        help="Text file containing one YouTube URL per line",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Destination LESSONS folder",
    )
    args = parser.parse_args()
    build_course(args.urls, args.output)


if __name__ == "__main__":
    main()

