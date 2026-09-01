# !pip install -q jiwer
"""
It measures Whisper transcription accuracy.
For every lesson folder, it compares:
- text.txt — correct/reference transcript
- raw_text.txt — Whisper’s transcript
It prints the Word Error Rate (WER) for each folder and one overall WER score.
Lower is better; 0% means an exact match.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
import os

from jiwer import wer

# C:\Users\PC\Desktop\kaggle\whisper\en\en_easy_stories
ROOT_DIR = Path(__file__).parent.parent.parent
DEFAULT_INPUT_ROOT = os.path.join(ROOT_DIR, "en", "en_easy_stories")

def normalize(text: str) -> str:
    """Normalize text before comparing the reference with Whisper output."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", "", text)
    return " ".join(text.split())


def calculate_all_wer(input_root: str | Path) -> None:
    """Print the WER for each folder and the overall WER across all folders."""
    root = Path(input_root)
    if not root.is_dir():
        raise FileNotFoundError(f"Input folder not found: {root}")

    references: list[str] = []
    transcripts: list[str] = []
    skipped = 0

    for folder in sorted(path for path in root.iterdir() if path.is_dir()):
        reference_path = folder / "text.txt"
        transcript_path = folder / "raw_text.txt"

        if not reference_path.is_file() or not transcript_path.is_file():
            print(f"Skipped {folder.name}: missing text.txt or raw_text.txt")
            skipped += 1
            continue

        reference = normalize(reference_path.read_text(encoding="utf-8"))
        transcript = normalize(transcript_path.read_text(encoding="utf-8"))
        if not reference:
            print(f"Skipped {folder.name}: text.txt is empty")
            skipped += 1
            continue

        score = wer(reference, transcript)
        print(f"{folder.name}: {score:.2%}")
        references.append(reference)
        transcripts.append(transcript)

    if references:
        overall_score = wer(" ".join(references), " ".join(transcripts))
        print(f"Overall WER ({len(references)} files): {overall_score:.2%}")
    else:
        print("No valid files were found.")

    if skipped:
        print(f"Skipped: {skipped} folder(s)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Calculate WER for all lesson folders in Whisper output."
    )
    parser.add_argument("--input-root", type=Path, default=DEFAULT_INPUT_ROOT)
    args = parser.parse_args()
    calculate_all_wer(args.input_root)


if __name__ == "__main__":
    main()
