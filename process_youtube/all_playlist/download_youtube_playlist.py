"""Build a course from a YouTube playlist.

The playlist URL, maximum video count, and course name are entered interactively.
Each video becomes a numbered lesson folder containing a named MP3, ``image.jpg``,
and ``raw_text.txt``. If English captions are unavailable, the text file is empty.
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

import yt_dlp
from yt_dlp.utils import DownloadError


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parents[1]

INVALID_WINDOWS_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
VTT_TAG = re.compile(r"<[^>]+>")

COURSE_DESCRIPTION_TEMPLATE = {
    "course_number": None,
    "course_name": None,
    "author": None,
    "content_language": None,
    "type": None,
    "audio_duration": None,
    "is_system_course": None,
    "avatar": None,
    "has_lesson_images": None,
    "level": None,
    "youtube_id": None,
    "url": None,
}

DEFAULT_LESSON_LEVEL = "b1"


def safe_title(title: str, max_length: int = 70) -> str:
    """Make a readable title safe for a Windows folder and filenames."""
    title = INVALID_WINDOWS_CHARS.sub("", html.unescape(title))
    title = re.sub(r"\s+", " ", title).strip().rstrip(".")
    return title[:max_length].rstrip(" .") or "Untitled lesson"


def create_course_description(course_dir: Path) -> Path:
    """Create a blank course description without replacing existing metadata."""
    description_dir = course_dir / "course_infos"
    description_dir.mkdir(parents=True, exist_ok=True)
    description_path = description_dir / "description.json"
    if not description_path.exists():
        description_path.write_text(
            json.dumps(COURSE_DESCRIPTION_TEMPLATE, indent=2) + "\n",
            encoding="utf-8",
        )
    return description_path


def create_lesson_description(
    lesson_dir: Path,
    lesson_number: int,
    lesson_name: str,
    info: dict,
) -> Path:
    """Create missing metadata inside a lesson folder without replacing edits."""
    description_path = lesson_dir / "description.json"
    if description_path.exists():
        return description_path

    video_id = info.get("id")
    duration = info.get("duration")
    try:
        audio_duration = round(float(duration), 2)
    except (TypeError, ValueError):
        audio_duration = 0.0

    description = {
        "lesson_number": lesson_number,
        "lesson_name": lesson_name,
        "level": DEFAULT_LESSON_LEVEL,
        "youtube_id": video_id,
        "url": (
            f"https://www.youtube.com/watch?v={video_id}"
            if video_id
            else info.get("webpage_url", "")
        ),
        "audio_start_time": 0,
        "audio_duration": audio_duration,
        "has_sentence_timestamps": False,
    }
    description_path.write_text(
        json.dumps(description, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return description_path


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


def playlist_video_urls(playlist_url: str, maximum_videos: int) -> list[str]:
    """Extract up to ``maximum_videos`` video URLs in playlist order."""
    options = {
        "extract_flat": "in_playlist",
        "playlistend": maximum_videos,
        "quiet": True,
        "no_warnings": True,
        "js_runtimes": {"node": {}},
    }
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(playlist_url, download=False)

    entries = info.get("entries") if info else None
    if not entries:
        return [playlist_url]

    urls: list[str] = []
    for entry in entries:
        if not entry:
            continue
        video_url = entry.get("webpage_url") or entry.get("url")
        if video_url and not video_url.startswith(("http://", "https://")):
            video_url = f"https://www.youtube.com/watch?v={entry.get('id', video_url)}"
        if video_url:
            urls.append(video_url)
    return urls[:maximum_videos]


def download_options(lesson_dir: Path, base_name: str, subtitle_language: str | None) -> dict:
    options = {
        "format": "bestaudio/best",
        "outtmpl": {
            "default": str(lesson_dir / f"{base_name}.%(ext)s"),
            "thumbnail": str(lesson_dir / "image.%(ext)s"),
            "subtitle": str(lesson_dir / "raw_text.%(ext)s"),
        },
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

    prefix = f"{index}. "
    # The folder name and MP3 filename repeat, so limit both to a safe Windows path.
    maximum_base_length = (235 - len(str(output_dir.resolve())) - 6) // 2
    maximum_title_length = max(20, maximum_base_length - len(prefix))
    lesson_name = html.unescape(
        info.get("title") or info.get("id") or "Untitled lesson"
    ).strip()
    title = safe_title(
        lesson_name,
        max_length=maximum_title_length,
    )
    base_name = f"{index}. {title}"
    lesson_dir = output_dir / base_name
    lesson_dir.mkdir(parents=True, exist_ok=True)

    expected_files = (
        lesson_dir / f"{base_name}.mp3",
        lesson_dir / "image.jpg",
        lesson_dir / "raw_text.txt",
    )
    if all(path.is_file() for path in expected_files):
        description_path = create_lesson_description(
            lesson_dir, index, lesson_name, info
        )
        print(f"[{index}] Already exists, skipping: {title}")
        print(f"    Lesson description: {description_path.name}")
        return

    subtitle_language = english_subtitle_language(info)
    print(f"[{index}] {title}")
    print(f"    English subtitles: {subtitle_language or 'not available (blank TXT)'}")

    with yt_dlp.YoutubeDL(
        download_options(lesson_dir, base_name, subtitle_language)
    ) as ydl:
        ydl.download([url])

    transcript_path = lesson_dir / "raw_text.txt"
    subtitle_files = sorted(lesson_dir.glob("raw_text*.vtt"))
    transcript = vtt_to_text(subtitle_files[0]) if subtitle_files else ""
    transcript_path.write_text(transcript, encoding="utf-8")

    for subtitle_file in subtitle_files:
        subtitle_file.unlink()

    description_path = create_lesson_description(
        lesson_dir, index, lesson_name, info
    )
    print(f"    Lesson description: {description_path.name}")


def build_course(playlist_url: str, maximum_videos: int, output_name: str) -> None:
    output_dir = PROJECT_DIR / "en" / safe_title(output_name, max_length=60) / "LESSONS"
    urls = playlist_video_urls(playlist_url, maximum_videos)
    if not urls:
        raise ValueError("No videos found in the playlist")

    output_dir.mkdir(parents=True, exist_ok=True)
    description_path = create_course_description(output_dir.parent)
    print(f"Course description: {description_path.resolve()}")
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
    playlist_url = input("YouTube playlist URL: ").strip()
    if not playlist_url:
        raise ValueError("YouTube playlist URL cannot be blank")

    maximum_text = input("Maximum number of videos to download: ").strip()
    try:
        maximum_videos = int(maximum_text)
    except ValueError as error:
        raise ValueError("Maximum number of videos must be a whole number") from error
    if maximum_videos < 1:
        raise ValueError("Maximum number of videos must be at least 1")

    output_name = input("Output/course name: ").strip()
    if not output_name:
        raise ValueError("Output/course name cannot be blank")

    build_course(playlist_url, maximum_videos, output_name)


if __name__ == "__main__":
    main()

