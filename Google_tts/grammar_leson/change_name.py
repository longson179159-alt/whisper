from pathlib import Path
import re

BASE_DIR = Path(__file__).resolve().parent
AUDIO_DIR = BASE_DIR / "grammar_leson_audio"
LESSONS_DIR = BASE_DIR / "lessons"


def safe_name(name):
    return re.sub(r"[^a-zA-Z0-9._-]", "_", name)


def rename_path(path, new_name):
    if new_name == path.name:
        return path

    destination = path.with_name(new_name)

    if destination.exists():
        raise FileExistsError(f"Cannot rename; already exists: {destination}")

    path.rename(destination)
    print(f"Renamed: {path.name} -> {destination.name}")
    return destination


# Rename the original MP3 files.
for audio_file in AUDIO_DIR.glob("*.mp3"):
    rename_path(audio_file, safe_name(audio_file.name))


# Rename each lesson's MP3 file, then rename its lesson folder.
for lesson_dir in sorted(path for path in LESSONS_DIR.iterdir() if path.is_dir()):
    for audio_file in lesson_dir.glob("*.mp3"):
        rename_path(audio_file, safe_name(audio_file.name))

    rename_path(lesson_dir, safe_name(lesson_dir.name))
