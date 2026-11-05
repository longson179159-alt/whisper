"""Split one long audio lesson into smaller lessons.

The script asks for the source lesson folder. It finds ``list_lessons.json``
at the course root and writes the resulting lessons to ``<course>/lessons``.
The source lesson remains unchanged.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path


TEMP_FOLDER_NAME = ".split_lessons_tmp"


def time_to_seconds(value: str) -> int:
    """Convert an HH:MM:SS or MM:SS value to seconds."""
    parts = value.split(":")
    if len(parts) not in (2, 3):
        raise ValueError(f"Invalid startTime: {value!r}")
    try:
        numbers = [int(part) for part in parts]
    except ValueError as error:
        raise ValueError(f"Invalid startTime: {value!r}") from error
    if any(number < 0 for number in numbers):
        raise ValueError(f"Invalid startTime: {value!r}")

    if len(numbers) == 2:
        minutes, seconds = numbers
        hours = 0
    else:
        hours, minutes, seconds = numbers
    if minutes >= 60 or seconds >= 60:
        raise ValueError(f"Invalid startTime: {value!r}")
    return hours * 3600 + minutes * 60 + seconds


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def write_json(path: Path, data) -> None:
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")


def find_course_and_split_list(source_lesson_dir: Path) -> tuple[Path, Path]:
    """Find the closest list_lessons.json at or above the source folder."""
    candidates = [
        source_lesson_dir,
        source_lesson_dir.parent,
        source_lesson_dir.parent.parent,
    ]
    for candidate in candidates:
        split_list_path = candidate / "list_lessons.json"
        if split_list_path.is_file():
            return candidate, split_list_path

    checked = "\n".join(
        f"  - {candidate / 'list_lessons.json'}" for candidate in candidates
    )
    raise FileNotFoundError(
        "Could not find list_lessons.json. Checked:\n" + checked
    )


def find_source_audio(source_lesson_dir: Path) -> Path:
    audio_files = sorted(source_lesson_dir.glob("*.mp3"))
    if len(audio_files) != 1:
        raise ValueError(
            f"Expected exactly one MP3 in {source_lesson_dir}, "
            f"found {len(audio_files)}"
        )
    return audio_files[0]


def load_source_timestamps(source_lesson_dir: Path) -> list[dict]:
    timestamp_path = source_lesson_dir / "raw_timestamp.json"
    if not timestamp_path.is_file():
        raise FileNotFoundError(f"Missing source timestamps: {timestamp_path}")
    data = load_json(timestamp_path)
    if isinstance(data, dict):
        data = data.get("segments", [])
    if not isinstance(data, list) or not data:
        raise ValueError(f"No timestamp segments found in {timestamp_path}")
    return data


def build_split_ranges(
    split_lessons: list[dict], source_end: float
) -> list[dict]:
    if not isinstance(split_lessons, list) or not split_lessons:
        raise ValueError("list_lessons.json must contain a non-empty JSON list")

    ranges = []
    seen_names = set()
    for index, lesson in enumerate(split_lessons):
        name = str(lesson["lessonFolderName"]).strip()
        if not name or Path(name).name != name:
            raise ValueError(f"Unsafe lesson folder name: {name!r}")
        if name in seen_names:
            raise ValueError(f"Duplicate lesson folder name: {name!r}")
        seen_names.add(name)

        start = time_to_seconds(lesson["startTime"])
        if index + 1 < len(split_lessons):
            end = time_to_seconds(split_lessons[index + 1]["startTime"])
        else:
            end = source_end
        if end <= start:
            raise ValueError(f"Invalid time range for {name}: {start} to {end}")
        ranges.append({"name": name, "start": start, "end": end})
    return ranges


def timestamps_for_range(
    source_timestamps: list[dict], start: float, end: float
) -> list[dict]:
    """Assign each source segment once, according to its midpoint."""
    result = []
    for segment in source_timestamps:
        segment_start = float(segment["start"])
        segment_end = float(segment["end"])
        midpoint = (segment_start + segment_end) / 2
        if start <= midpoint < end:
            result.append(
                {
                    **segment,
                    "start": round(max(segment_start, start) - start, 3),
                    "end": round(min(segment_end, end) - start, 3),
                }
            )
    return result


def export_audio_clip(
    source_audio: Path, output_audio: Path, start: float, end: float
) -> None:
    command = [
        "ffmpeg",
        "-y",
        "-ss",
        str(start),
        "-i",
        str(source_audio),
        "-t",
        str(end - start),
        "-vn",
        "-map",
        "0:a:0",
        "-c:a",
        "libmp3lame",
        "-b:a",
        "192k",
        str(output_audio),
    ]
    subprocess.run(command, check=True)


def create_lesson(
    temporary_lesson_dir: Path,
    lesson_number: int,
    lesson_range: dict,
    source_audio: Path,
    source_timestamps: list[dict],
    source_description: dict,
    level_override: str | None,
) -> None:
    temporary_lesson_dir.mkdir(parents=True)
    start = lesson_range["start"]
    end = lesson_range["end"]
    name = lesson_range["name"]
    timestamps = timestamps_for_range(source_timestamps, start, end)
    raw_text = "\n".join(
        str(segment.get("text", "")).strip()
        for segment in timestamps
        if str(segment.get("text", "")).strip()
    )

    export_audio_clip(
        source_audio,
        temporary_lesson_dir / "audio.mp3",
        start,
        end,
    )
    write_json(temporary_lesson_dir / "raw_timestamp.json", timestamps)
    (temporary_lesson_dir / "raw_text.txt").write_text(
        raw_text + ("\n" if raw_text else ""), encoding="utf-8"
    )
    (temporary_lesson_dir / "text.txt").write_text("", encoding="utf-8")

    description = {
        "lesson_number": lesson_number,
        "lesson_name": name,
        "level": level_override or source_description.get("level") or "c1",
        "youtube_id": source_description.get("youtube_id"),
        "url": source_description.get("url"),
        "audio_start_time": 0,
        "audio_duration": round(end - start, 2),
        "has_sentence_timestamps": True,
        "youtube_subtitle": source_description.get("youtube_subtitle"),
        "media_source": "audio",
    }
    write_json(temporary_lesson_dir / "description.json", description)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Split one long audio lesson into smaller lessons."
    )
    parser.add_argument(
        "--level",
        help="Override the source lesson level for every generated lesson.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing generated lesson folders.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_value = input("Input source lesson folder: ").strip().strip('"')
    if not input_value:
        raise ValueError("Input source lesson folder cannot be blank")

    source_lesson_dir = Path(input_value).expanduser().resolve()
    if not source_lesson_dir.is_dir():
        raise FileNotFoundError(
            f"Source lesson folder does not exist: {source_lesson_dir}"
        )

    course_dir, split_list_path = find_course_and_split_list(source_lesson_dir)
    output_lessons_dir = course_dir / "lessons"
    temporary_output_dir = course_dir / TEMP_FOLDER_NAME
    description_path = source_lesson_dir / "description.json"
    if not description_path.is_file():
        raise FileNotFoundError(f"Missing source description: {description_path}")
    if temporary_output_dir.exists():
        raise FileExistsError(
            f"Temporary output already exists: {temporary_output_dir}. "
            "Check and remove it before rerunning."
        )

    source_audio = find_source_audio(source_lesson_dir)
    source_timestamps = load_source_timestamps(source_lesson_dir)
    source_description = load_json(description_path)
    split_lessons = load_json(split_list_path)

    timestamp_end = max(float(item["end"]) for item in source_timestamps)
    description_end = float(source_description.get("audio_duration") or 0)
    source_end = max(timestamp_end, description_end)
    ranges = build_split_ranges(split_lessons, source_end)

    existing_targets = [
        output_lessons_dir / lesson_range["name"]
        for lesson_range in ranges
        if (output_lessons_dir / lesson_range["name"]).exists()
    ]
    if existing_targets and not args.overwrite:
        paths = "\n".join(f"  - {path}" for path in existing_targets)
        raise FileExistsError(
            "Output lesson folders already exist. "
            "Use --overwrite to replace them:\n" + paths
        )

    print(f"Source lesson: {source_lesson_dir}")
    print(f"Split list: {split_list_path}")
    print(f"Output folder: {output_lessons_dir}")
    output_lessons_dir.mkdir(parents=True, exist_ok=True)
    temporary_output_dir.mkdir()

    try:
        for lesson_number, lesson_range in enumerate(ranges, start=1):
            print(
                f"Creating {lesson_range['name']}: "
                f"{lesson_range['start']}s to {lesson_range['end']}s"
            )
            create_lesson(
                temporary_output_dir / lesson_range["name"],
                lesson_number,
                lesson_range,
                source_audio,
                source_timestamps,
                source_description,
                args.level,
            )

        for lesson_range in ranges:
            name = lesson_range["name"]
            target = output_lessons_dir / name
            if target.exists():
                shutil.rmtree(target)
            shutil.move(str(temporary_output_dir / name), str(target))
            print(f"Saved: {target}")
    finally:
        if temporary_output_dir.exists():
            shutil.rmtree(temporary_output_dir)


if __name__ == "__main__":
    main()
