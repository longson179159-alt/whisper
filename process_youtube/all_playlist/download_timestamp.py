"""Backfill missing YouTube subtitle timestamps for downloaded lessons.

The script scans lesson ``description.json`` files below ``en``, reuses each
saved YouTube URL, and writes ``raw_timestamp.json`` beside the lesson media.
Existing timestamp files are preserved unless ``--overwrite`` is supplied.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

import yt_dlp
from yt_dlp.utils import DownloadError


PROJECT_DIR = Path(__file__).resolve().parents[2]
EN_DIR = PROJECT_DIR / "en"
TEMP_SUBTITLE_STEM = ".raw_timestamp_download"
WHITESPACE = re.compile(r"[ \t\r\f\v]+")
SEGMENT_END = re.compile(r'''(?:[.!?…]["'”’\)\]]*|♪|\])$''')
TIMESTAMPED_SUBTITLE_TYPES = {"professional", "auto_generated"}


def youtube_url(description: dict) -> str | None:
    """Return the saved URL, falling back to the saved YouTube video ID."""
    url = description.get("url")
    if isinstance(url, str) and url.strip():
        return url.strip()

    video_id = description.get("youtube_id")
    if isinstance(video_id, str) and video_id.strip():
        return f"https://www.youtube.com/watch?v={video_id.strip()}"
    return None


def clean_caption_text(value: str) -> str:
    """Normalize a caption and replace its line breaks with spaces."""
    lines: list[str] = []
    for line in html.unescape(value).replace("\u200b", "").splitlines():
        cleaned = WHITESPACE.sub(" ", line).strip()
        if cleaned:
            lines.append(cleaned)
    return " ".join(lines)


def merge_caption_sentences(timestamps: list[dict]) -> list[dict]:
    """Merge consecutive caption chunks until sentence-ending punctuation."""
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

        # Songs commonly use a closing music note instead of punctuation, and
        # non-speech captions such as "[MUSIC]" should remain separate events.
        if SEGMENT_END.search(current["text"]):
            current["ts_idx"] = len(merged)
            merged.append(current)
            current = None

    if current is not None:
        current["ts_idx"] = len(merged)
        merged.append(current)

    return merged


def event_text(event: dict) -> str:
    """Return viewer-facing text from one JSON3 event."""
    return clean_caption_text(
        "".join(
            segment.get("utf8", "")
            for segment in event.get("segs", [])
            if isinstance(segment, dict)
        )
    )


def professional_timestamps(data: dict) -> list[dict]:
    """Convert manual captions and merge them at sentence or lyric boundaries."""
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
                "ts_idx": len(timestamps),
            }
        )

    return merge_caption_sentences(timestamps)


def auto_generated_timestamps(data: dict) -> list[dict]:
    """Keep short auto-caption events, removing only same-time duplicates."""
    events: list[dict] = []
    seen_pieces: set[tuple[int, str]] = set()

    for event in data.get("events", []):
        if "tStartMs" not in event:
            continue

        event_start_ms = int(event["tStartMs"])
        pieces: list[str] = []
        for segment in event.get("segs", []):
            if not isinstance(segment, dict):
                continue
            piece = clean_caption_text(str(segment.get("utf8", "")))
            if not piece:
                continue

            piece_start_ms = event_start_ms + int(segment.get("tOffsetMs") or 0)
            duplicate_key = (piece_start_ms, piece.casefold())
            if duplicate_key in seen_pieces:
                continue
            seen_pieces.add(duplicate_key)
            pieces.append(str(segment.get("utf8", "")))

        text = clean_caption_text("".join(pieces))
        if not text:
            continue

        duration_ms = int(event.get("dDurationMs") or 0)
        events.append(
            {
                "start": round(event_start_ms / 1000, 3),
                "declared_end": round((event_start_ms + duration_ms) / 1000, 3),
                "text": text,
            }
        )

    events.sort(key=lambda timestamp: timestamp["start"])
    timestamps: list[dict] = []
    for index, event in enumerate(events):
        start = event["start"]
        end = event["declared_end"]
        if index + 1 < len(events):
            next_start = events[index + 1]["start"]
            if next_start > start:
                end = min(end, next_start)
        if end <= start:
            continue

        timestamps.append(
            {
                "start": start,
                "end": end,
                "text": event["text"],
                "ts_idx": len(timestamps),
            }
        )

    return timestamps


def json3_to_timestamps(json3_path: Path, subtitle_type: str) -> list[dict]:
    """Convert yt-dlp JSON3 captions using the source-appropriate strategy."""
    data = json.loads(json3_path.read_text(encoding="utf-8-sig"))
    if subtitle_type == "auto_generated":
        return auto_generated_timestamps(data)
    return professional_timestamps(data)


def english_subtitle_details(info: dict, preferred_type: str | None) -> tuple[str, str]:
    """Return the best English caption language and its source type."""
    sources = [
        ("subtitles", "professional"),
        ("automatic_captions", "auto_generated"),
    ]
    if preferred_type in TIMESTAMPED_SUBTITLE_TYPES:
        sources.sort(key=lambda item: item[1] != preferred_type)

    for source_name, subtitle_type in sources:
        languages = info.get(source_name) or {}
        english = [
            language
            for language in languages
            if language.lower() == "en" or language.lower().startswith("en-")
        ]
        if english:
            language = sorted(
                english, key=lambda value: (value.lower() != "en", value)
            )[0]
            return language, subtitle_type

    raise ValueError("English subtitles are no longer available")


def ydl_base_options() -> dict:
    return {
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "js_runtimes": {"node": {}},
    }


def remove_temporary_subtitles(lesson_dir: Path) -> None:
    for path in lesson_dir.glob(f"{TEMP_SUBTITLE_STEM}*"):
        if path.is_file():
            path.unlink()


def update_timestamp_metadata(
    description_path: Path,
    description: dict,
    subtitle_type: str | None = None,
) -> None:
    changed = description.get("has_sentence_timestamps") is not True
    description["has_sentence_timestamps"] = True
    if subtitle_type and description.get("youtube_subtitle") != subtitle_type:
        description["youtube_subtitle"] = subtitle_type
        changed = True
    if changed:
        description_path.write_text(
            json.dumps(description, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


def download_lesson(lesson_dir: Path, url: str, overwrite: bool = False) -> str:
    """Download one timestamp file. Return ``written`` or ``skipped``."""
    description_path = lesson_dir / "description.json"
    description = json.loads(description_path.read_text(encoding="utf-8-sig"))
    output_path = lesson_dir / "raw_timestamp.json"
    if output_path.is_file() and not overwrite:
        update_timestamp_metadata(description_path, description)
        return "skipped"

    remove_temporary_subtitles(lesson_dir)
    with yt_dlp.YoutubeDL(ydl_base_options()) as ydl:
        info = ydl.extract_info(url, download=False)

    language, subtitle_type = english_subtitle_details(
        info, description.get("youtube_subtitle")
    )
    options = ydl_base_options()
    options.update(
        {
            "skip_download": True,
            "writesubtitles": subtitle_type == "professional",
            "writeautomaticsub": subtitle_type == "auto_generated",
            "subtitleslangs": [language],
            "subtitlesformat": "json3",
            "overwrites": True,
            "outtmpl": {
                "subtitle": str(lesson_dir / f"{TEMP_SUBTITLE_STEM}.%(ext)s"),
                "default": str(lesson_dir / f"{TEMP_SUBTITLE_STEM}.%(ext)s"),
            },
        }
    )

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            ydl.download([url])

        downloaded = sorted(lesson_dir.glob(f"{TEMP_SUBTITLE_STEM}*.json3"))
        if not downloaded:
            raise FileNotFoundError("yt-dlp did not create a JSON3 subtitle file")

        timestamps = json3_to_timestamps(downloaded[0], subtitle_type)
        if not timestamps:
            raise ValueError("the downloaded subtitle contains no caption events")

        output_path.write_text(
            json.dumps(timestamps, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        update_timestamp_metadata(description_path, description, subtitle_type)
    finally:
        remove_temporary_subtitles(lesson_dir)

    return "written"


def lesson_descriptions(course_names: set[str] | None) -> list[Path]:
    """Find lesson descriptions in current and level-nested course layouts."""
    descriptions: list[Path] = []
    for description_path in EN_DIR.rglob("description.json"):
        lesson_dir = description_path.parent
        if lesson_dir.parent.name.casefold() != "lessons":
            continue

        course_name = lesson_dir.parent.parent.name
        if course_names and course_name.casefold() not in course_names:
            continue
        descriptions.append(description_path)

    def sort_key(path: Path) -> tuple[str, int, str]:
        course = path.parent.parent.parent.name.casefold()
        match = re.match(r"(\d+)", path.parent.name)
        lesson_number = int(match.group(1)) if match else 10**9
        return course, lesson_number, path.parent.name.casefold()

    return sorted(descriptions, key=sort_key)


def run(
    course_names: set[str] | None,
    overwrite: bool,
    dry_run: bool,
    subtitle_type_filter: str | None,
) -> int:
    written = 0
    planned = 0
    skipped = 0
    unavailable = 0
    failures: list[str] = []

    for description_path in lesson_descriptions(course_names):
        lesson_dir = description_path.parent
        label = str(lesson_dir.relative_to(EN_DIR))
        try:
            description = json.loads(description_path.read_text(encoding="utf-8-sig"))
            output_path = lesson_dir / "raw_timestamp.json"
            if output_path.is_file() and not overwrite:
                if not dry_run:
                    update_timestamp_metadata(description_path, description)
                skipped += 1
                print(f"[SKIP] {label}: raw_timestamp.json already exists")
                continue

            subtitle_type = description.get("youtube_subtitle")
            if subtitle_type_filter and subtitle_type != subtitle_type_filter:
                continue
            if subtitle_type not in TIMESTAMPED_SUBTITLE_TYPES:
                unavailable += 1
                print(f"[NONE] {label}: subtitles are {subtitle_type or 'unknown'}")
                continue

            url = youtube_url(description)
            if url is None:
                raise ValueError("description has no YouTube URL or video ID")

            if dry_run:
                planned += 1
                print(f"[TODO] {label}")
                continue

            result = download_lesson(lesson_dir, url, overwrite=overwrite)
            if result == "written":
                written += 1
                print(f"[OK]   {label}")
            else:
                skipped += 1
                print(f"[SKIP] {label}")
        except (DownloadError, OSError, ValueError, json.JSONDecodeError) as error:
            failures.append(f"{label}: {error}")
            print(f"[FAIL] {label}: {error}")

    planned_text = f", {planned} planned" if dry_run else ""
    print(
        f"\nFinished: {written} written{planned_text}, {skipped} skipped, "
        f"{unavailable} without subtitles, {len(failures)} failed"
    )
    return 1 if failures else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill missing raw_timestamp.json files from saved YouTube URLs"
    )
    parser.add_argument(
        "--course",
        action="append",
        help="Process only this course name; repeat for multiple courses.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace raw_timestamp.json files that already exist.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List work without downloading or changing description files.",
    )
    parser.add_argument(
        "--subtitle-type",
        choices=sorted(TIMESTAMPED_SUBTITLE_TYPES),
        help="Process only professional or auto-generated subtitles.",
    )
    return parser.parse_args()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = parse_args()
    course_names = {name.casefold() for name in args.course} if args.course else None
    return run(
        course_names,
        overwrite=args.overwrite,
        dry_run=args.dry_run,
        subtitle_type_filter=args.subtitle_type,
    )


if __name__ == "__main__":
    raise SystemExit(main())
