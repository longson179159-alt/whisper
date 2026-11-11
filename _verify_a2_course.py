import json
import re
from pathlib import Path


root = Path(r"C:\Users\PC\Desktop\a2\LEARN ENGLISH PODCAST 17 TIPS TO HELP YOU SPEAK FLUENT ENGLISH FAST")
audio_dir = root / "LEARN ENGLISH PODCAST 17 TIPS TO HELP YOU SPEAK FLUENT ENGLISH FAST_audios"
lessons_dir = root / "lessons"
safe = re.compile(r"^[a-zA-Z0-9._-]+$")

course_files = list(root.glob("course_infos/description.json"))
folders = sorted(path for path in lessons_dir.iterdir() if path.is_dir())
descriptions = [path / "description.json" for path in folders]
mp3s = sorted(root.rglob("*.mp3"))

course_data = json.loads(course_files[0].read_text(encoding="utf-8"))
lesson_data = [json.loads(path.read_text(encoding="utf-8")) for path in descriptions]
course_non_null = [key for key, value in course_data.items() if value is not None]
lesson_non_null = [[key for key, value in data.items() if value is not None] for data in lesson_data]
lesson_mp3_counts = {folder.name: len(list(folder.glob("*.mp3"))) for folder in folders}
lesson_txt_counts = {folder.name: len(list(folder.glob("*.txt"))) for folder in folders}
matching = {
    folder.name: all(mp3.stem == folder.name for mp3 in folder.glob("*.mp3"))
    for folder in folders
}

print(f"course_descriptions={len(course_files)}")
print(f"lesson_folders={len(folders)}")
print(f"lesson_descriptions={sum(path.is_file() for path in descriptions)}")
print(f"course_non_null={course_non_null}")
print(f"lesson_non_null={lesson_non_null}")
print(f"safe_folders={all(safe.fullmatch(folder.name) for folder in folders)}")
print(f"safe_mp3s={all(safe.fullmatch(mp3.name) for mp3 in mp3s)}")
print(f"matching_lesson_mp3_stems={matching}")
print(f"lesson_mp3_counts={lesson_mp3_counts}")
print(f"lesson_txt_counts={lesson_txt_counts}")
print("folders=" + repr([folder.name for folder in folders]))
print("mp3s=" + repr([str(mp3.relative_to(root)) for mp3 in mp3s]))
