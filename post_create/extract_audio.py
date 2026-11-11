
from pathlib import Path
import shutil

ROOT = Path(r"C:\Users\PC\Desktop\kaggle\whisper\en")

total_courses = 0
total_audios = 0

for course_infos in ROOT.rglob("course_infos"):
    course_folder = course_infos.parent
    lessons_folder = course_folder / "lessons"

    if not lessons_folder.is_dir():
        continue

    output_folder = course_folder / f"{course_folder.name}_audios"
    output_folder.mkdir(exist_ok=True)

    count = 0

    for lesson_folder in sorted(lessons_folder.iterdir()):
        if not lesson_folder.is_dir():
            continue

        source_audio = lesson_folder / "audio.mp3"

        if not source_audio.is_file():
            print(f"[MISSING] {source_audio}")
            continue

        destination = output_folder / f"{lesson_folder.name}.mp3"

        if destination.exists():
            print(f"[SKIPPED] {destination.name}")
            continue

        shutil.copy2(source_audio, destination)

        print(f"[COPIED] {destination.name}")
        count += 1
        total_audios += 1

    total_courses += 1
    print(f"\n[COURSE] {course_folder.name}: {count} audios\n")

print("=" * 50)
print(f"Courses processed: {total_courses}")
print(f"Audios copied: {total_audios}")
print("Done!")
