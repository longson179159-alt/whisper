from pathlib import Path


course_root = Path(r"C:\Users\PC\Desktop\a2\LEARN ENGLISH PODCAST 17 TIPS TO HELP YOU SPEAK FLUENT ENGLISH FAST")
source = '''import re
from pathlib import Path


COURSE_ROOT = Path(__file__).resolve().parent
AUDIO_FOLDER_NAME = "LEARN ENGLISH PODCAST 17 TIPS TO HELP YOU SPEAK FLUENT ENGLISH FAST_audios"
SAFE_NAME_PATTERN = re.compile(r"[^a-zA-Z0-9._-]")


def safe_name(name: str) -> str:
    return SAFE_NAME_PATTERN.sub("_", name)


def rename_to(path: Path, destination: Path) -> Path:
    if destination == path:
        return path
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite existing path: {destination}")
    path.rename(destination)
    return destination


def rename_safely(path: Path) -> Path:
    return rename_to(path, path.with_name(safe_name(path.name)))


def main() -> None:
    audio_dir = COURSE_ROOT / AUDIO_FOLDER_NAME
    lessons_dir = COURSE_ROOT / "lessons"

    if audio_dir.is_dir():
        for mp3 in sorted(audio_dir.glob("*.mp3")):
            rename_safely(mp3)

    if lessons_dir.is_dir():
        lesson_folders = sorted(path for path in lessons_dir.iterdir() if path.is_dir())
        for lesson_folder in lesson_folders:
            mp3s = sorted(lesson_folder.glob("*.mp3"))
            if len(mp3s) == 1:
                destination = lesson_folder / f"{safe_name(lesson_folder.name)}{mp3s[0].suffix}"
                rename_to(mp3s[0], destination)
            else:
                for mp3 in mp3s:
                    rename_safely(mp3)
        for lesson_folder in lesson_folders:
            rename_safely(lesson_folder)


if __name__ == "__main__":
    main()
'''
(course_root / "change_name.py").write_text(source, encoding="utf-8")
exec(compile(source, str(course_root / "change_name.py"), "exec"), {"__name__": "__main__", "__file__": str(course_root / "change_name.py")})
