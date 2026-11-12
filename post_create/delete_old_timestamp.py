
from pathlib import Path

ROOT = Path(r"C:\Users\PC\Desktop\kaggle\whisper\en")

FILES_TO_DELETE = {
    "raw_timestamp.json",
    "timestamp.json",
    "youtube_timestamp.json",
    "word_timestamp.json",
    
}

DRY_RUN = False  # Change to False to actually delete files

total_deleted = 0

for lessons_folder in ROOT.rglob("lessons"):
    if not lessons_folder.is_dir():
        continue

    for lesson_folder in lessons_folder.iterdir():
        if not lesson_folder.is_dir():
            continue

        for filename in FILES_TO_DELETE:
            file_path = lesson_folder / filename

            if file_path.is_file():
                if DRY_RUN:
                    print(f"[WOULD DELETE] {file_path}")
                else:
                    file_path.unlink()
                    print(f"[DELETED] {file_path}")

                total_deleted += 1

print("=" * 50)
print(f"Files found: {total_deleted}")
print(f"Dry run: {DRY_RUN}")
print("Done!")