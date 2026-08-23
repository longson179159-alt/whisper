"""Run this file in Google Colab after placing MP3 files in AUDIO_DIR."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

subprocess.run(
    [sys.executable, "-m", "pip", "install", "-q", "openai-whisper", "opencc-python-reimplemented"],
    check=True,
)
subprocess.run(["apt-get", "update", "-qq"], check=True)
subprocess.run(["apt-get", "install", "-y", "-qq", "ffmpeg"], check=True)

import torch
import whisper
from IPython.display import Audio, FileLink, display
from opencc import OpenCC

# Put your MP3 files in this folder in Colab, or change this path to your
# Google Drive folder after mounting Drive.
AUDIO_DIR = Path("/content/funny_chinese_stories")
output_root = Path("/content/whisper_output")

if not AUDIO_DIR.is_dir():
    raise FileNotFoundError(
        f"Audio folder not found: {AUDIO_DIR}. "
        "Upload/create the folder in Colab, then run this script again."
    )

audio_files = sorted(AUDIO_DIR.glob("*.mp3"))
if not audio_files:
    raise FileNotFoundError(f"No MP3 files found in: {AUDIO_DIR}")

device = "cuda" if torch.cuda.is_available() else "cpu"
model = whisper.load_model("small", device=device)
# "tiny", "base", "small", "medium", "large"

output_root.mkdir(parents=True, exist_ok=True)
cc = OpenCC("t2s")

for audio_path in audio_files:
    print(f"\nTranscribing: {audio_path.name}")
    display(Audio(str(audio_path)))

    audio_name = audio_path.stem
    lesson_folder = output_root / audio_name
    lesson_folder.mkdir(exist_ok=True)

    copied_audio = lesson_folder / "audio"
    shutil.copy2(audio_path, copied_audio)

    result = model.transcribe(
        str(audio_path),
        language="zh",
        fp16=(device == "cuda"),
    )

    timestamp_data = [
        {
            "start": segment["start"],
            "end": segment["end"],
            "text": cc.convert(segment["text"].strip()),
        }
        for segment in result["segments"]
    ]

    with open(lesson_folder / "raw_timestamp.json", "w", encoding="utf-8") as f:
        json.dump(timestamp_data, f, ensure_ascii=False, indent=4)

    transcript = "\n".join(item["text"] for item in timestamp_data)

    with open(lesson_folder / "raw_text.txt", "w", encoding="utf-8") as f:
        f.write(transcript)

    simplified_text = cc.convert(transcript)

    if simplified_text != transcript:
        print(f"{audio_name} audio transcribed to Traditional Chinese")

    with open(lesson_folder / "text.txt", "w", encoding="utf-8") as f:
        f.write(simplified_text)

    print(transcript[:100])
    print(f"Saved to: {lesson_folder}")

zip_path = shutil.make_archive(str(output_root), "zip", str(output_root))

print("\nFinished.")
display(FileLink(zip_path))


# Compress-Archive -Path "C:\Users\PC\Desktop\paddle\funny_chinese_stories" -DestinationPath "C:\Users\PC\Desktop\paddle\funny_chinese_stories.zip"
