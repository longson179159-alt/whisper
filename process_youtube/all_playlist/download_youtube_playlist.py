"""Build a course from a YouTube playlist.

The playlist URL, maximum video count, and course name are entered interactively.
Each video becomes a numbered lesson folder containing a named MP3, ``image.jpg``,
and ``youtube_subtitle.txt``. If English captions are unavailable, the text file
is empty.
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

DEFAULT_LESSON_LEVEL = "b1"


def safe_title(title: str, max_length: int = 70) -> str:
    """Make a readable title safe for a Windows folder and filenames."""
    title = INVALID_WINDOWS_CHARS.sub("", html.unescape(title))
    title = re.sub(r"\s+", " ", title).strip().rstrip(".")
    return title[:max_length].rstrip(" .") or "Untitled lesson"

def create_course_description(
    course_dir: Path,
    course_name: str,
    audio_duration: float,
    youtube_id: str | None = None,
    url: str | None = None,
    level: str | None = None,
) -> Path:
    """Create the course metadata, leaving uncertain values as JSON null."""
    description_dir = course_dir / "course_infos"
    description_dir.mkdir(parents=True, exist_ok=True)
    description_path = description_dir / "description.json"
    description = {
        "course_number": None,
        "course_name": course_name,
        "author": None,
        "content_language": None,
        "type": None,
        "audio_duration": round(audio_duration, 2),
        "is_system_course": None,
        "avatar": None,
        "has_lesson_images": True,
        "level": level,
        "youtube_id": youtube_id,
        "url": url,
    }
    description_path.write_text(
        json.dumps(description, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return description_path


def audio_duration_from_info(info: dict) -> float:
    """Return a usable duration for one video, or zero when unavailable."""
    try:
        return float(info.get("duration") or 0)
    except (TypeError, ValueError):
        return 0.0


def create_lesson_description(
    lesson_dir: Path,
    lesson_number: int,
    lesson_name: str,
    info: dict,
    subtitle_type: str,
    level: str = DEFAULT_LESSON_LEVEL,
) -> Path:
    """Create lesson metadata and add new fields without replacing old values."""
    description_path = lesson_dir / "description.json"
    if description_path.exists():
        description = json.loads(description_path.read_text(encoding="utf-8"))
        changed = False
        if description.get("level") != level:
            description["level"] = level
            changed = True
        if "youtube_subtitle" not in description:
            description["youtube_subtitle"] = subtitle_type
            changed = True
        if changed:
            description_path.write_text(
                json.dumps(description, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        return description_path

    video_id = info.get("id")
    audio_duration = round(audio_duration_from_info(info), 2)

    description = {
        "lesson_number": lesson_number,
        "lesson_name": lesson_name,
        "level": level,
        "youtube_id": video_id,
        "url": (
            f"https://www.youtube.com/watch?v={video_id}"
            if video_id
            else info.get("webpage_url", "")
        ),
        "audio_start_time": 0,
        "audio_duration": audio_duration,
        "has_sentence_timestamps": False,
        "youtube_subtitle": subtitle_type,
    }
    description_path.write_text(
        json.dumps(description, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return description_path


def english_subtitle_details(info: dict) -> tuple[str | None, str]:
    """Return the preferred English caption language and caption type."""
    sources = (
        ("subtitles", "professional"),
        ("automatic_captions", "auto_generated"),
    )
    for source_name, subtitle_type in sources:
        languages = info.get(source_name) or {}
        english = [
            language
            for language in languages
            if language.lower() == "en" or language.lower().startswith("en-")
        ]
        if english:
            language = sorted(
                english, key=lambda value: (value != "en", value)
            )[0]
            return language, subtitle_type
    return None, "not_available"


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


def playlist_video_urls(
    playlist_url: str, maximum_videos: int
) -> tuple[list[str], dict]:
    """Extract video URLs and playlist metadata in playlist order."""
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
        return [playlist_url], info or {}

    urls: list[str] = []
    for entry in entries:
        if not entry:
            continue
        video_url = entry.get("webpage_url") or entry.get("url")
        if video_url and not video_url.startswith(("http://", "https://")):
            video_url = f"https://www.youtube.com/watch?v={entry.get('id', video_url)}"
        if video_url:
            urls.append(video_url)
    return urls[:maximum_videos], info


def download_options(
    lesson_dir: Path,
    base_name: str,
    subtitle_language: str | None,
    subtitle_type: str,
) -> dict:
    options = {
        "format": "bestaudio/best",
        "outtmpl": {
            "default": str(lesson_dir / f"{base_name}.%(ext)s"),
            "thumbnail": str(lesson_dir / "image.%(ext)s"),
            "subtitle": str(lesson_dir / "youtube_subtitle.%(ext)s"),
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
                "writesubtitles": subtitle_type == "professional",
                "writeautomaticsub": subtitle_type == "auto_generated",
                "subtitleslangs": [subtitle_language],
                "subtitlesformat": "vtt",
            }
        )

    return options


def save_timestamps_if_requested(
    lesson_dir: Path,
    url: str,
    subtitle_type: str,
    enabled: bool,
) -> None:
    """Create raw_timestamp.json for available English captions when requested."""
    if not enabled or subtitle_type not in {"professional", "auto_generated"}:
        return

    from download_timestamp import download_lesson as download_timestamps

    result = download_timestamps(lesson_dir, url, overwrite=False)
    print(f"    Timestamps: {result}")


def download_lesson(
    index: int,
    url: str,
    output_dir: Path,
    save_professional_timestamps: bool = False,
    lesson_level: str = DEFAULT_LESSON_LEVEL,
) -> float:
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
    subtitle_language, subtitle_type = english_subtitle_details(info)

    expected_files = (
        lesson_dir / f"{base_name}.mp3",
        lesson_dir / "image.jpg",
        lesson_dir / "youtube_subtitle.txt",
    )
    if all(path.is_file() for path in expected_files):
        description_path = create_lesson_description(
            lesson_dir, index, lesson_name, info, subtitle_type, lesson_level
        )
        save_timestamps_if_requested(
            lesson_dir, url, subtitle_type, save_professional_timestamps
        )
        print(f"[{index}] Already exists, skipping: {title}")
        print(f"    Lesson description: {description_path.name}")
        return audio_duration_from_info(info)

    print(f"[{index}] {title}")
    print(f"    English subtitles: {subtitle_type}")

    with yt_dlp.YoutubeDL(
        download_options(lesson_dir, base_name, subtitle_language, subtitle_type)
    ) as ydl:
        ydl.download([url])

    transcript_path = lesson_dir / "youtube_subtitle.txt"
    subtitle_files = sorted(lesson_dir.glob("youtube_subtitle*.vtt"))
    transcript = vtt_to_text(subtitle_files[0]) if subtitle_files else ""
    transcript_path.write_text(transcript, encoding="utf-8")

    for subtitle_file in subtitle_files:
        subtitle_file.unlink()

    description_path = create_lesson_description(
        lesson_dir, index, lesson_name, info, subtitle_type, lesson_level
    )
    save_timestamps_if_requested(
        lesson_dir, url, subtitle_type, save_professional_timestamps
    )
    print(f"    Lesson description: {description_path.name}")
    return audio_duration_from_info(info)


def build_course(playlist_url: str, maximum_videos: int, output_name: str) -> None:
    course_name = safe_title(output_name, max_length=60)
    output_dir = PROJECT_DIR / "en" / course_name / "lessons"
    urls, playlist_info = playlist_video_urls(playlist_url, maximum_videos)
    if not urls:
        raise ValueError("No videos found in the playlist")

    output_dir.mkdir(parents=True, exist_ok=True)
    failures: list[tuple[int, str]] = []
    audio_duration = 0.0

    for index, url in enumerate(urls, start=1):
        try:
            audio_duration += download_lesson(index, url, output_dir)
        except DownloadError as error:
            failures.append((index, url))
            print(f"[{index}] Download failed: {error}")

    description_path = create_course_description(
        output_dir.parent,
        course_name,
        audio_duration,
        youtube_id=playlist_info.get("id"),
        url=playlist_url,
    )
    print(f"Course description: {description_path.resolve()}")

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

