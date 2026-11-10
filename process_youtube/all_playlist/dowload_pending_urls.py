"""Build a course from URLs in ``peding.txt`` as a standalone downloader."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

import yt_dlp
from yt_dlp.utils import DownloadError


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parents[1]
URL_FILE = SCRIPT_DIR / "peding.txt"
VALID_LEVELS = ("a1", "a2", "b1", "b2", "c1", "c2")
INVALID_WINDOWS_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
VTT_TAG = re.compile(r"<[^>]+>")
WHITESPACE = re.compile(r"[ \t\r\f\v]+")
SEGMENT_END = re.compile(r'''(?:[.!?。！？…]["'”’\)\]]*|♪|\])$''')
TEMP_SUBTITLE_STEM = ".raw_timestamp_download"


def safe_title(title: str, max_length: int = 70) -> str:
    title = INVALID_WINDOWS_CHARS.sub("", html.unescape(title))
    title = re.sub(r"\s+", " ", title).strip().rstrip(".")
    return title[:max_length].rstrip(" .") or "Untitled lesson"


def read_urls(url_file: Path = URL_FILE) -> list[str]:
    return [
        line.strip()
        for line in url_file.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def base_ydl_options() -> dict:
    return {
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "js_runtimes": {"node": {}},
    }


def audio_duration_from_info(info: dict) -> float:
    try:
        return float(info.get("duration") or 0)
    except (TypeError, ValueError):
        return 0.0


def simplified_chinese_subtitle_details(
    info: dict, preferred_type: str | None = None
) -> tuple[str | None, str]:
    """Return the preferred Simplified Chinese language and caption type."""
    sources = [
        ("subtitles", "professional"),
        ("automatic_captions", "auto_generated"),
    ]
    if preferred_type in {"professional", "auto_generated"}:
        sources.sort(key=lambda item: item[1] != preferred_type)

    priority = {"zh-hans": 0, "zh-cn": 1, "zh-sg": 2, "zh": 3}
    for source_name, subtitle_type in sources:
        languages = info.get(source_name) or {}
        matches = [
            language
            for language in languages
            if language.lower() == "zh"
            or language.lower().startswith(("zh-hans", "zh-cn", "zh-sg"))
        ]
        if matches:
            language = sorted(
                matches,
                key=lambda value: (priority.get(value.lower(), 4), value),
            )[0]
            return language, subtitle_type
    return None, "not_available"


def create_course_description(
    course_dir: Path, course_name: str, audio_duration: float, level: str
) -> Path:
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
        "is_system_course": True,
        "avatar": None,
        "has_lesson_images": True,
        "level": level,
        "youtube_id": None,
        "url": None,
    }
    description_path.write_text(
        json.dumps(description, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return description_path


def create_lesson_description(
    lesson_dir: Path,
    lesson_number: int,
    lesson_name: str,
    info: dict,
    subtitle_type: str,
    level: str,
) -> Path:
    description_path = lesson_dir / "description.json"
    if description_path.exists():
        description = json.loads(description_path.read_text(encoding="utf-8-sig"))
    else:
        video_id = info.get("id")
        description = {
            "lesson_number": lesson_number,
            "lesson_name": lesson_name,
            "youtube_id": video_id,
            "url": (
                f"https://www.youtube.com/watch?v={video_id}"
                if video_id
                else info.get("webpage_url", "")
            ),
            "audio_start_time": 0,
            "audio_duration": round(audio_duration_from_info(info), 2),
        }
    description["level"] = level
    description["media_source"] = "audio"
    description["has_sentence_timestamps"] = True
    description["youtube_subtitle"] = subtitle_type
    description_path.write_text(
        json.dumps(description, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return description_path


def vtt_to_text(vtt_path: Path) -> str:
    output_lines: list[str] = []
    in_note = False
    for raw_line in vtt_path.read_text(
        encoding="utf-8-sig", errors="replace"
    ).splitlines():
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


def media_download_options(
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
            {"key": "FFmpegThumbnailsConvertor", "format": "jpg"},
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


def clean_caption_text(value: str) -> str:
    lines: list[str] = []
    for line in html.unescape(value).replace("\u200b", "").splitlines():
        cleaned = WHITESPACE.sub(" ", line).strip()
        if cleaned:
            lines.append(cleaned)
    return " ".join(lines)


def event_text(event: dict) -> str:
    return clean_caption_text(
        "".join(
            segment.get("utf8", "")
            for segment in event.get("segs", [])
            if isinstance(segment, dict)
        )
    )


def merge_caption_sentences(timestamps: list[dict]) -> list[dict]:
    merged: list[dict] = []
    current: dict | None = None
    for timestamp in timestamps:
        text = clean_caption_text(str(timestamp.get("text", "")))
        if not text:
            continue
        if current is None:
            current = {
                "start": timestamp["start"],
                "end": timestamp["end"],
                "text": text,
            }
        else:
            current["end"] = timestamp["end"]
            current["text"] = f'{current["text"]} {text}'
        if SEGMENT_END.search(current["text"]):
            current["ts_idx"] = len(merged)
            merged.append(current)
            current = None
    if current is not None:
        current["ts_idx"] = len(merged)
        merged.append(current)
    return merged


def professional_timestamps(data: dict) -> list[dict]:
    timestamps: list[dict] = []
    for event in data.get("events", []):
        if "tStartMs" not in event:
            continue
        text = event_text(event)
        if not text:
            continue
        start_ms = int(event["tStartMs"])
        duration_ms = int(event.get("dDurationMs") or 0)
        timestamps.append(
            {
                "start": round(start_ms / 1000, 3),
                "end": round((start_ms + duration_ms) / 1000, 3),
                "text": text,
            }
        )
    return merge_caption_sentences(timestamps)


def auto_generated_timestamps(data: dict) -> list[dict]:
    events: list[dict] = []
    seen: set[tuple[int, str]] = set()
    for event in data.get("events", []):
        if "tStartMs" not in event:
            continue
        event_start_ms = int(event["tStartMs"])
        pieces: list[str] = []
        for segment in event.get("segs", []):
            if not isinstance(segment, dict):
                continue
            piece = clean_caption_text(str(segment.get("utf8", "")))
            piece_start_ms = event_start_ms + int(segment.get("tOffsetMs") or 0)
            key = (piece_start_ms, piece.casefold())
            if not piece or key in seen:
                continue
            seen.add(key)
            pieces.append(str(segment.get("utf8", "")))
        text = clean_caption_text("".join(pieces))
        if text:
            duration_ms = int(event.get("dDurationMs") or 0)
            events.append(
                {
                    "start": round(event_start_ms / 1000, 3),
                    "declared_end": round(
                        (event_start_ms + duration_ms) / 1000, 3
                    ),
                    "text": text,
                }
            )
    events.sort(key=lambda item: item["start"])
    timestamps: list[dict] = []
    for index, event in enumerate(events):
        start = event["start"]
        end = event["declared_end"]
        if index + 1 < len(events) and events[index + 1]["start"] > start:
            end = min(end, events[index + 1]["start"])
        if end > start:
            timestamps.append(
                {
                    "start": start,
                    "end": end,
                    "text": event["text"],
                    "ts_idx": len(timestamps),
                }
            )
    return timestamps


def remove_temporary_subtitles(lesson_dir: Path) -> None:
    for path in lesson_dir.glob(f"{TEMP_SUBTITLE_STEM}*"):
        if path.is_file():
            path.unlink()


def save_timestamps(
    lesson_dir: Path,
    info: dict,
    subtitle_language: str | None,
    subtitle_type: str,
) -> str:
    output_path = lesson_dir / "raw_timestamp.json"
    if output_path.is_file():
        return "skipped"
    if not subtitle_language or subtitle_type == "not_available":
        return "not_available"

    remove_temporary_subtitles(lesson_dir)
    options = base_ydl_options()
    options.update(
        {
            "skip_download": True,
            "writesubtitles": subtitle_type == "professional",
            "writeautomaticsub": subtitle_type == "auto_generated",
            "subtitleslangs": [subtitle_language],
            "subtitlesformat": "json3",
            "overwrites": True,
            "outtmpl": {
                "subtitle": str(lesson_dir / f"{TEMP_SUBTITLE_STEM}.%(ext)s"),
                "default": str(lesson_dir / f"{TEMP_SUBTITLE_STEM}.%(ext)s"),
            },
        }
    )
    url = info.get("webpage_url") or f'https://www.youtube.com/watch?v={info["id"]}'
    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            ydl.download([url])
        downloaded = sorted(lesson_dir.glob(f"{TEMP_SUBTITLE_STEM}*.json3"))
        if not downloaded:
            raise FileNotFoundError("yt-dlp did not create a JSON3 subtitle file")
        data = json.loads(downloaded[0].read_text(encoding="utf-8-sig"))
        timestamps = (
            auto_generated_timestamps(data)
            if subtitle_type == "auto_generated"
            else professional_timestamps(data)
        )
        if not timestamps:
            raise ValueError("the downloaded subtitle contains no caption events")
        output_path.write_text(
            json.dumps(timestamps, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    finally:
        remove_temporary_subtitles(lesson_dir)
    return "written"


def download_lesson(index: int, url: str, output_dir: Path, level: str) -> float:
    with yt_dlp.YoutubeDL(base_ydl_options()) as ydl:
        info = ydl.extract_info(url, download=False)

    prefix = f"{index}. "
    maximum_base_length = (235 - len(str(output_dir.resolve())) - 6) // 2
    title = safe_title(
        info.get("title") or info.get("id") or "Untitled lesson",
        max_length=max(20, maximum_base_length - len(prefix)),
    )
    lesson_name = html.unescape(info.get("title") or title).strip()
    base_name = f"{index}. {title}"
    lesson_dir = output_dir / base_name
    lesson_dir.mkdir(parents=True, exist_ok=True)
    subtitle_language, subtitle_type = simplified_chinese_subtitle_details(info)

    expected_files = (
        lesson_dir / f"{base_name}.mp3",
        lesson_dir / "image.jpg",
        lesson_dir / "youtube_subtitle.txt",
    )
    if all(path.is_file() for path in expected_files):
        print(f"[{index}] Already exists, skipping: {title}")
    else:
        print(f"[{index}] {title}")
        print(f"    Simplified Chinese subtitles: {subtitle_type}")
        with yt_dlp.YoutubeDL(
            media_download_options(
                lesson_dir, base_name, subtitle_language, subtitle_type
            )
        ) as ydl:
            ydl.download([url])
        subtitle_files = sorted(lesson_dir.glob("youtube_subtitle*.vtt"))
        transcript = vtt_to_text(subtitle_files[0]) if subtitle_files else ""
        (lesson_dir / "youtube_subtitle.txt").write_text(
            transcript, encoding="utf-8"
        )
        for subtitle_file in subtitle_files:
            subtitle_file.unlink()

    description_path = create_lesson_description(
        lesson_dir, index, lesson_name, info, subtitle_type, level
    )
    timestamp_result = save_timestamps(
        lesson_dir, info, subtitle_language, subtitle_type
    )
    print(f"    Lesson description: {description_path.name}")
    print(f"    Timestamps: {timestamp_result}")
    return audio_duration_from_info(info)


def build_course(output_name: str, level: str) -> None:
    urls = read_urls()
    if not urls:
        raise ValueError(f"No YouTube URLs found in {URL_FILE}")

    course_name = safe_title(output_name, max_length=60)
    output_dir = PROJECT_DIR / "en" / course_name / "lessons"
    output_dir.mkdir(parents=True, exist_ok=True)
    failures: list[tuple[int, str, str]] = []
    audio_duration = 0.0
    for index, url in enumerate(urls, start=1):
        try:
            audio_duration += download_lesson(index, url, output_dir, level)
        except (DownloadError, OSError, ValueError, json.JSONDecodeError) as error:
            failures.append((index, url, str(error)))
            print(f"[{index}] Failed: {error}")

    description_path = create_course_description(
        output_dir.parent, course_name, audio_duration, level
    )
    print(f"Course description: {description_path.resolve()}")
    print(f"\nFinished: {len(urls) - len(failures)}/{len(urls)} lessons processed")
    print(f"Course folder: {output_dir.resolve()}")
    if failures:
        print("Failed URLs:")
        for index, url, error in failures:
            print(f"  {index}. {url} ({error})")


def main() -> None:
    output_name = input("Output/course name: ").strip()
    if not output_name:
        raise ValueError("Output/course name cannot be blank")
    level = input("CEFR level (a1, a2, b1, b2, c1, c2): ").strip().lower()
    if level not in VALID_LEVELS:
        raise ValueError(
            f"Invalid CEFR level {level!r}; choose one of: {', '.join(VALID_LEVELS)}"
        )
    build_course(output_name, level)


if __name__ == "__main__":
    main()
