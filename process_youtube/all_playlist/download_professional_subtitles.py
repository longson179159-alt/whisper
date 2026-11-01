"""Download manual English YouTube captions as timestamped JSON.

Run without arguments to process every professional-caption lesson in the
configured courses::

    python download_professional_subtitles.py

Existing ``raw_timestamp.json`` files are preserved. Pass ``--overwrite`` to
download them again, or ``--course "TED-Ed"`` to process selected courses.
"""

from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path

import yt_dlp
from yt_dlp.utils import DownloadError


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parents[1]
EN_DIR = PROJECT_DIR / "en"

COURSES = (
    "Frankenstein",
    "Romeo and Juliet",
    "Ted Talks",
    "TED-Ed",
    "To Fluency",
    "VOA Learning English",
)

WHITESPACE = re.compile(r"[ \t\r\f\v]+")
SENTENCE_END = re.compile(r'''[.!?…]["'”’\)\]]*$''')
TEMP_SUBTITLE_STEM = ".raw_timestamp_download"


def youtube_url(description: dict) -> str | None:
    """Get a usable YouTube URL from one lesson description."""
    url = description.get("url")
    if isinstance(url, str) and url.strip():
        return url.strip()

    video_id = description.get("youtube_id")
    if isinstance(video_id, str) and video_id.strip():
        return f"https://www.youtube.com/watch?v={video_id.strip()}"
    return None


def professional_english_language(info: dict) -> str | None:
    """Return the preferred manual English subtitle language, if present."""
    subtitles = info.get("subtitles") or {}
    english = [
        language
        for language in subtitles
        if language.lower() == "en" or language.lower().startswith("en-")
    ]
    if not english:
        return None
    return sorted(english, key=lambda value: (value.lower() != "en", value))[0]


def clean_caption_text(value: str) -> str:
    """Normalize a caption and replace its line breaks with spaces."""
    lines = []
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

        if SENTENCE_END.search(current["text"]):
            current["ts_idx"] = len(merged)
            merged.append(current)
            current = None

    if current is not None:
        current["ts_idx"] = len(merged)
        merged.append(current)

    return merged


def clean_existing_timestamp_files(root: Path) -> tuple[int, int]:
    """Normalize and merge captions in existing timestamp files."""
    files_changed = 0
    text_fields_changed = 0

    for timestamp_path in sorted(root.rglob("raw_timestamp.json")):
        timestamps = json.loads(timestamp_path.read_text(encoding="utf-8-sig"))
        normalized = merge_caption_sentences(timestamps)
        if normalized != timestamps:
            text_fields_changed += len(timestamps)
            timestamp_path.write_text(
                json.dumps(normalized, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            files_changed += 1

    return files_changed, text_fields_changed


def json3_to_timestamps(json3_path: Path) -> list[dict]:
    """Convert yt-dlp's YouTube JSON3 subtitles to the requested structure."""
    data = json.loads(json3_path.read_text(encoding="utf-8-sig"))
    timestamps: list[dict] = []

    for event in data.get("events", []):
        if "tStartMs" not in event:
            continue

        text = clean_caption_text(
            "".join(
                segment.get("utf8", "")
                for segment in event.get("segs", [])
                if isinstance(segment, dict)
            )
        )
        if not text:
            continue

        start_ms = int(event["tStartMs"])
        duration_ms = int(event.get("dDurationMs") or 0)
        start = round(start_ms / 1000, 3)
        end = round((start_ms + duration_ms) / 1000, 3)

        timestamps.append(
            {
                "start": start,
                "end": end,
                "text": text,
                "ts_idx": len(timestamps),
            }
        )

    return merge_caption_sentences(timestamps)


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


def download_lesson(lesson_dir: Path, url: str, overwrite: bool) -> str:
    """Download and convert one lesson. Return ``written`` or ``skipped``."""
    output_path = lesson_dir / "raw_timestamp.json"
    if output_path.is_file() and not overwrite:
        return "skipped"

    remove_temporary_subtitles(lesson_dir)

    with yt_dlp.YoutubeDL(ydl_base_options()) as ydl:
        info = ydl.extract_info(url, download=False)

    language = professional_english_language(info)
    if language is None:
        raise ValueError("manual English subtitles are no longer available")

    options = ydl_base_options()
    options.update(
        {
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": False,
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

        timestamps = json3_to_timestamps(downloaded[0])
        if not timestamps:
            raise ValueError("the downloaded subtitle contains no caption events")

        output_path.write_text(
            json.dumps(timestamps, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    finally:
        remove_temporary_subtitles(lesson_dir)

    return "written"


def professional_lessons(course_name: str) -> list[tuple[Path, str]]:
    """Find lessons currently marked as having professional subtitles."""
    lessons_dir = EN_DIR / course_name / "LESSONS"
    if not lessons_dir.is_dir():
        raise FileNotFoundError(f"Course lessons folder not found: {lessons_dir}")

    lessons: list[tuple[Path, str]] = []
    for description_path in lessons_dir.glob("*/description.json"):
        description = json.loads(description_path.read_text(encoding="utf-8-sig"))
        if description.get("youtube_subtitle") != "professional":
            continue

        url = youtube_url(description)
        if url is None:
            print(f"[FAIL] {course_name} / {description_path.parent.name}: missing URL")
            continue
        lessons.append((description_path.parent, url))

    def lesson_number(item: tuple[Path, str]) -> tuple[int, str]:
        match = re.match(r"(\d+)", item[0].name)
        return (int(match.group(1)) if match else 10**9, item[0].name.casefold())

    return sorted(lessons, key=lesson_number)


def run(course_names: list[str], overwrite: bool) -> int:
    written = 0
    skipped = 0
    failures: list[str] = []

    for course_name in course_names:
        try:
            lessons = professional_lessons(course_name)
        except (OSError, json.JSONDecodeError) as error:
            failures.append(f"{course_name}: {error}")
            print(f"[FAIL] {course_name}: {error}")
            continue

        print(f"\n{course_name}: {len(lessons)} professional lesson(s)")
        for lesson_dir, url in lessons:
            label = f"{course_name} / {lesson_dir.name}"
            try:
                result = download_lesson(lesson_dir, url, overwrite)
                if result == "skipped":
                    skipped += 1
                    print(f"[SKIP] {label}")
                else:
                    written += 1
                    print(f"[OK]   {label}")
            except (DownloadError, OSError, ValueError, json.JSONDecodeError) as error:
                failures.append(f"{label}: {error}")
                print(f"[FAIL] {label}: {error}")

    print(
        f"\nFinished: {written} written, {skipped} skipped, "
        f"{len(failures)} failed"
    )
    if failures:
        print("Failures:")
        for failure in failures:
            print(f"  - {failure}")
    return 1 if failures else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download manual English captions as raw_timestamp.json"
    )
    parser.add_argument(
        "--course",
        action="append",
        choices=COURSES,
        help="Process only this course; repeat the option for multiple courses.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace raw_timestamp.json files that already exist.",
    )
    parser.add_argument(
        "--clean-existing",
        action="store_true",
        help="Normalize and merge existing timestamp captions; do not download.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.clean_existing:
        files_changed, text_fields_changed = clean_existing_timestamp_files(EN_DIR)
        print(
            f"Cleaned {text_fields_changed} text field(s) "
            f"in {files_changed} raw_timestamp.json file(s)"
        )
        return
    raise SystemExit(run(args.course or list(COURSES), args.overwrite))


if __name__ == "__main__":
    main()
