import json
import re
from pathlib import Path


COURSE_ROOT = Path(r"C:\Users\PC\Desktop\a2\LEARN ENGLISH PODCAST 17 TIPS TO HELP YOU SPEAK FLUENT ENGLISH FAST")
COURSE_NAME = "LEARN ENGLISH PODCAST 17 TIPS TO HELP YOU SPEAK FLUENT ENGLISH FAST"
AUDIO_FOLDER_NAME = "LEARN ENGLISH PODCAST 17 TIPS TO HELP YOU SPEAK FLUENT ENGLISH FAST_audios"


def lesson_name(folder_name: str) -> str:
    return re.sub(r"^\d+\.?\s*", "", folder_name)


course_description = {
    "course_number": None,
    "course_name": COURSE_NAME,
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

lesson_template = {
    "lesson_number": None,
    "lesson_name": None,
    "level": None,
    "youtube_id": None,
    "url": None,
    "audio_start_time": None,
    "audio_duration": None,
    "has_sentence_timestamps": None,
}

course_info_dir = COURSE_ROOT / "course_infos"
course_info_dir.mkdir(exist_ok=True)
(course_info_dir / "description.json").write_text(
    json.dumps(course_description, indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8",
)

lessons_dir = COURSE_ROOT / "lessons"
for folder in sorted(path for path in lessons_dir.iterdir() if path.is_dir()):
    description = dict(lesson_template)
    description["lesson_name"] = lesson_name(folder.name)
    (folder / "description.json").write_text(
        json.dumps(description, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

change_name_source = '''import re
from pathlib import Path


COURSE_ROOT = Path(__file__).resolve().parent
AUDIO_FOLDER_NAME = "LEARN ENGLISH PODCAST 17 TIPS TO HELP YOU SPEAK FLUENT ENGLISH FAST_audios"
SAFE_NAME_PATTERN = re.compile(r"[^a-zA-Z0-9._-]")


def safe_name(name: str) -> str:
    return SAFE_NAME_PATTERN.sub("_", name)


def rename_safely(path: Path) -> Path:
    destination = path.with_name(safe_name(path.name))
    if destination == path:
        return path
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite existing path: {destination}")
    path.rename(destination)
    return destination


def main() -> None:
    audio_dir = COURSE_ROOT / AUDIO_FOLDER_NAME
    lessons_dir = COURSE_ROOT / "lessons"

    if audio_dir.is_dir():
        for mp3 in sorted(audio_dir.glob("*.mp3")):
            rename_safely(mp3)

    if lessons_dir.is_dir():
        lesson_folders = sorted(path for path in lessons_dir.iterdir() if path.is_dir())
        for lesson_folder in lesson_folders:
            for mp3 in sorted(lesson_folder.glob("*.mp3")):
                rename_safely(mp3)
        for lesson_folder in lesson_folders:
            rename_safely(lesson_folder)


if __name__ == "__main__":
    main()
'''
(COURSE_ROOT / "change_name.py").write_text(change_name_source, encoding="utf-8")

exec(compile(change_name_source, str(COURSE_ROOT / "change_name.py"), "exec"), {"__name__": "__main__", "__file__": str(COURSE_ROOT / "change_name.py")})
