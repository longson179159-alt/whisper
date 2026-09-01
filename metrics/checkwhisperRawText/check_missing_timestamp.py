"""Check that every master Whisper timestamp appears in one lesson file.

Run from this folder:
    python check_missing_timestamp.py
"""

import json
from collections import Counter, defaultdict
from pathlib import Path


BOOK_DIR = Path(__file__).resolve().parent
LESSONS_DIR = BOOK_DIR / "lessons"
MASTER_TIMESTAMPS_PATH = BOOK_DIR / "raw_timestamp.json"
LIST_PATHS = (BOOK_DIR / "list_lessons.json", BOOK_DIR / "list_lesson.json")


def to_seconds(value: str) -> float:
    """Convert M:SS.ss or H:MM:SS.ss into seconds."""
    parts = value.split(":")
    if len(parts) == 2:
        minutes, seconds = parts
        return int(minutes) * 60 + float(seconds)
    if len(parts) == 3:
        hours, minutes, seconds = parts
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    raise ValueError(f"Invalid startTime: {value}")


def timestamp_key(timestamp: dict) -> tuple[float, float, str]:
    """Round float noise while retaining timestamp identity and transcript text."""
    return (
        round(float(timestamp["start"]), 3),
        round(float(timestamp["end"]), 3),
        timestamp["text"].strip(),
    )


def load_json(path: Path):
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def find_lesson_list() -> Path:
    for path in LIST_PATHS:
        if path.exists():
            return path
    names = ", ".join(path.name for path in LIST_PATHS)
    raise FileNotFoundError(f"Could not find a lesson list ({names}).")


def print_entries(title: str, entries: list[dict]) -> None:
    print(f"\n{title}: {len(entries)}")
    for entry in entries:
        print(
            f"  {entry['start']:.3f}–{entry['end']:.3f}: "
            f"{entry['text']}"
        )


def main() -> None:
    master_timestamps = load_json(MASTER_TIMESTAMPS_PATH)
    lesson_list = load_json(find_lesson_list())

    master_counts = Counter(timestamp_key(item) for item in master_timestamps)
    master_entries = defaultdict(list)
    for item in master_timestamps:
        master_entries[timestamp_key(item)].append(item)

    actual_counts: Counter = Counter()
    actual_entries = defaultdict(list)
    missing_files: list[Path] = []

    for lesson in lesson_list:
        folder_name = lesson["lessonFolderName"]
        lesson_start = to_seconds(lesson["startTime"])
        timestamp_path = LESSONS_DIR / folder_name / "raw_timestamp.json"

        if not timestamp_path.exists():
            missing_files.append(timestamp_path)
            continue

        # createSmallLessons.py stores local timestamps, so add the lesson start
        # to recover the original master-timestamp values for comparison.
        for item in load_json(timestamp_path):
            original = {
                **item,
                "start": item["start"] + lesson_start,
                "end": item["end"] + lesson_start,
            }
            key = timestamp_key(original)
            actual_counts[key] += 1
            actual_entries[key].append(original)

    missing_keys = list((master_counts - actual_counts).elements())
    extra_keys = list((actual_counts - master_counts).elements())
    missing_entries = [master_entries[key].pop() for key in missing_keys]
    extra_entries = [actual_entries[key].pop() for key in extra_keys]

    print(f"Master timestamps: {len(master_timestamps)}")
    print(f"Lesson timestamps: {sum(actual_counts.values())}")
    print(f"Missing lesson files: {len(missing_files)}")
    for path in missing_files:
        print(f"  {path}")

    print_entries("Missing timestamps", missing_entries)
    print_entries("Unexpected or duplicated timestamps", extra_entries)

    if missing_files or missing_entries or extra_entries:
        raise SystemExit(1)

    print("\nPASS: Every master timestamp appears exactly once in the lesson files.")


if __name__ == "__main__":
    main()

# python youtube_data\The_alchemist_chapters\check_missing_timestamp.py