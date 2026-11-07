
import argparse
import json
import os
import re
from urllib.parse import parse_qs, urlparse

from pydub import AudioSegment


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGE_EXTENSIONS = (
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".bmp",
    ".gif",
    ".tif",
    ".tiff",
)


def get_course_path():
    folder_path = input(
        "Enter the course folder path (for example, en/English_history): "
    ).strip().strip('"')

    if not folder_path:
        raise ValueError("The course folder path cannot be empty.")

    if not os.path.isabs(folder_path):
        folder_path = os.path.join(PROJECT_ROOT, folder_path)

    course_path = os.path.abspath(folder_path)
    if not os.path.isdir(course_path):
        raise FileNotFoundError(f"Course folder not found: {course_path}")

    return course_path


def get_level():
    level = input("Enter the lesson level (default: b1): ").strip()
    return level or "b1"


def get_folder_lesson_number(folder_name):
    match = re.match(r"\s*(\d+)", folder_name)
    return int(match.group(1)) if match else None


def lesson_folder_sort_key(folder_name):
    lesson_number = get_folder_lesson_number(folder_name)
    if lesson_number is not None:
        return (0, lesson_number, folder_name.lower())
    return (1, 0, folder_name.lower())


def find_lesson_media(lessons_path):
    lessons = []

    for folder_name in sorted(os.listdir(lessons_path), key=lesson_folder_sort_key):
        lesson_path = os.path.join(lessons_path, folder_name)
        if not os.path.isdir(lesson_path):
            continue

        files = os.listdir(lesson_path)
        audio_files = [name for name in files if name.lower().endswith(".mp3")]
        image_files = [
            name for name in files if name.lower().endswith(IMAGE_EXTENSIONS)
        ]

        if len(audio_files) != 1:
            raise ValueError(
                f"Expected exactly one MP3 in {lesson_path}, found {len(audio_files)}."
            )
        if len(image_files) > 1:
            raise ValueError(
                f"Expected at most one image in {lesson_path}, "
                f"found {len(image_files)}."
            )
        if image_files and not image_files[0].lower().endswith((".jpg", ".jpeg")):
            raise ValueError(
                f"The lesson image must be JPG/JPEG before it can be renamed to "
                f"image.jpg: {os.path.join(lesson_path, image_files[0])}"
            )

        image_name = image_files[0] if image_files else None
        lessons.append((folder_name, lesson_path, audio_files[0], image_name))

    if not lessons:
        raise ValueError(f"No lesson folders found in {lessons_path}")

    return lessons


def rename_media(source_path, target_path):
    if os.path.basename(source_path) == os.path.basename(target_path):
        return

    if os.path.exists(target_path) and not os.path.samefile(source_path, target_path):
        raise FileExistsError(f"Cannot rename because the target exists: {target_path}")

    # A temporary name also handles case-only renames safely on Windows.
    if os.path.exists(target_path):
        temporary_path = target_path + ".rename_tmp"
        if os.path.exists(temporary_path):
            raise FileExistsError(f"Temporary rename target exists: {temporary_path}")
        os.rename(source_path, temporary_path)
        os.rename(temporary_path, target_path)
    else:
        os.rename(source_path, target_path)


def read_json_if_exists(json_path):
    if not os.path.exists(json_path):
        return {}

    with open(json_path, "r", encoding="utf-8") as file:
        return json.load(file)


def write_json(json_path, data):
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


def create_lesson_description(
    lesson_path,
    folder_name,
    lesson_number,
    audio_duration,
    level,
    is_youtube_video,
):
    description_path = os.path.join(lesson_path, "description.json")
    old_description = read_json_if_exists(description_path)

    youtube_id = None
    if is_youtube_video:
        url = old_description.get("url") or ""
        youtube_id = parse_qs(urlparse(url).query).get("v", [None])[0]

    defaults = {
        "lesson_number": lesson_number,
        "lesson_name": folder_name,
        "level": level,
        "youtube_id": youtube_id,
        "url": "",
        "audio_start_time": 0,
        "audio_duration": round(audio_duration, 2),
        "has_sentence_timestamps": True,
    }
    description = {**defaults, **old_description}
    if description.get("audio_duration") is None:
        description["audio_duration"] = round(audio_duration, 2)
    description["lesson_number"] = lesson_number
    description["level"] = level
    description["has_sentence_timestamps"] = True
    write_json(description_path, description)


def create_course_description(course_path, total_audio_duration, level):
    description_path = os.path.join(course_path, "course_infos", "description.json")
    old_description = read_json_if_exists(description_path)

    defaults = {
        "course_number": None,
        "course_name": None,
        "author": None,
        "content_language": None,
        "type": None,
        "audio_duration": round(total_audio_duration, 2),
        "is_system_course": True,
        "avatar": None,
        "has_lesson_images": None,
        "level": None,
        "youtube_id": None,
        "url": None,
    }
    course_description = {**defaults, **old_description}
    course_description["audio_duration"] = round(total_audio_duration, 2)
    course_description["level"] = level
    course_description["is_system_course"] = True
    write_json(description_path, course_description)


def main():
    parser = argparse.ArgumentParser(
        description="Standardize lesson media and create lesson/course descriptions."
    )
    parser.add_argument(
        "--is_youtube_video",
        action="store_true",
        help="Extract a YouTube ID from an existing lesson URL",
    )
    args = parser.parse_args()

    course_path = get_course_path()
    level = get_level()
    lessons_path = os.path.join(course_path, "lessons")
    if not os.path.isdir(lessons_path):
        raise FileNotFoundError(f"Lessons folder not found: {lessons_path}")

    # Validate every lesson before changing any files.
    lessons = find_lesson_media(lessons_path)
    total_audio_duration = 0

    for fallback_number, (folder_name, lesson_path, audio_name, image_name) in enumerate(
        lessons, start=1
    ):
        lesson_number = get_folder_lesson_number(folder_name) or fallback_number
        audio_path = os.path.join(lesson_path, audio_name)
        standard_audio_path = os.path.join(lesson_path, "audio.mp3")

        rename_media(audio_path, standard_audio_path)
        if image_name:
            image_path = os.path.join(lesson_path, image_name)
            standard_image_path = os.path.join(lesson_path, "image.jpg")
            rename_media(image_path, standard_image_path)

        audio_duration = AudioSegment.from_mp3(standard_audio_path).duration_seconds
        total_audio_duration += audio_duration

        create_lesson_description(
            lesson_path=lesson_path,
            folder_name=folder_name,
            lesson_number=lesson_number,
            audio_duration=audio_duration,
            level=level,
            is_youtube_video=args.is_youtube_video,
        )
        print(f"Finished lesson: {folder_name}")

    create_course_description(course_path, total_audio_duration, level)
    print(f"Finished course: {course_path}")
    print(f"Total course audio duration: {round(total_audio_duration, 2)} seconds")


if __name__ == "__main__":
    main()


# Example:
# python add_timestamp/add_description.py
