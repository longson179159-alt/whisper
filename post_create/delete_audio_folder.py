from pathlib import Path
import shutil

ROOT = Path(r"C:\Users\PC\Desktop\kaggle\whisper\en")

if not ROOT.is_dir():
    raise FileNotFoundError(f"Root folder not found: {ROOT}")

# Find matching audio folders
audio_folders = sorted(
    folder
    for folder in ROOT.rglob("*")
    if folder.is_dir()
    and folder.name == f"{folder.parent.name}_audios"
)

if not audio_folders:
    print("No matching audio folders found.")
    raise SystemExit

print(f"\nFound {len(audio_folders)} audio folders:\n")

for folder in audio_folders:
    print(folder)

# Confirm before deleting
confirm = input(
    f"\nDelete all {len(audio_folders)} folders? Type YES to confirm: "
).strip()

if confirm != "YES":
    print("Cancelled. Nothing deleted.")
    raise SystemExit

# Delete folders
for folder in audio_folders:
    shutil.rmtree(folder)
    print(f"Deleted: {folder}")

print(f"\nDone! Deleted {len(audio_folders)} audio folders.")
