# !pip install -q jiwer
"""
It measures Whisper Chinese-transcription accuracy.
For every lesson folder, it compares:
- text.txt — correct/reference transcript
- raw_text.txt — Whisper’s transcript
It prints the Character Error Rate (CER) for each folder and one overall CER score.
Lower is better; 0% means an exact match.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from jiwer import cer


DEFAULT_INPUT_ROOT = Path(
    r"C:\Users\PC\Desktop\paddle\zh"
)


def normalize(text: str) -> str:
    """Keep Chinese characters and remove spaces and punctuation."""
    return re.sub(r"[^\u4e00-\u9fff]", "", text)


def calculate_all_cer(input_root: str | Path) -> None:
    """Print the CER for each folder and the overall CER across all folders."""
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

        score = cer(reference, transcript)
        print(f"{folder.name}: {score:.2%}")
        references.append(reference)
        transcripts.append(transcript)

    if references:
        overall_score = cer("".join(references), "".join(transcripts))
        print(f"Overall CER ({len(references)} files): {overall_score:.2%}")
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
    calculate_all_cer(args.input_root)


if __name__ == "__main__":
    main()
