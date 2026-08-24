"""Report real-text sentences that Whisper did not match.

This script reads lesson files only.  It never changes text.txt,
raw_timestamp.json, timestamp.json, or audio files.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
HELPER_DIR = PROJECT_ROOT / "add_timestamp"
if str(HELPER_DIR) not in sys.path:
    sys.path.insert(0, str(HELPER_DIR))

from helper import clean_word, get_lists_txt, nw_ref_match_flags


DEFAULT_INPUT_ROOT = PROJECT_ROOT / "youtube_data" / "little_prince" / "lessons"
DEFAULT_OUTPUT_NAME = "missing_text_report.json"


def get_whisper_words(raw_timestamp_path: Path) -> list[str]:
    """Return normalized words from Whisper's raw timestamp segments."""
    with raw_timestamp_path.open(encoding="utf-8") as file:
        data = json.load(file)

    if isinstance(data, dict):
        segments = data.get("segments", [])
    elif isinstance(data, list):
        segments = data
    else:
        raise ValueError("Raw timestamp JSON must be a list or contain 'segments'.")

    words: list[str] = []
    for segment in segments:
        for word in str(segment.get("text", "")).split():
            normalized = clean_word(word)
            if normalized:
                words.append(normalized)
    return words


def build_lesson_report(lesson_folder: Path, low_confidence_threshold: float) -> dict[str, Any]:
    """Compare one lesson's real text with its raw Whisper transcription."""
    text_path = lesson_folder / "text.txt"
    raw_timestamp_path = lesson_folder / "raw_timestamp.json"
    list_ref, list_id = get_lists_txt(text_path)
    whisper_words = get_whisper_words(raw_timestamp_path)
    alignment = nw_ref_match_flags(list_ref, whisper_words)

    sentences: dict[tuple[int, int], dict[str, Any]] = {}
    for item, alignment_item in zip(list_id, alignment):
        word, paragraph_index, sentence_index, _ = item
        if not clean_word(word):
            continue
        matched = alignment_item[1] == 1
        key = (paragraph_index, sentence_index)
        if key not in sentences:
            sentences[key] = {
                "paragraph_index": paragraph_index,
                "sentence_index": sentence_index,
                "words": [],
                "total_words": 0,
                "matched_words": 0,
            }

        sentence = sentences[key]
        sentence["words"].append(word)
        sentence["total_words"] += 1
        if matched:
            sentence["matched_words"] += 1

    sentence_reports: list[dict[str, Any]] = []
    paragraphs: dict[int, dict[str, Any]] = defaultdict(
        lambda: {"total_words": 0, "matched_words": 0, "sentence_count": 0}
    )

    for sentence in sentences.values():
        total_words = sentence["total_words"]
        matched_words = sentence["matched_words"]
        match_rate = matched_words / total_words if total_words else 0.0
        status = (
            "missing"
            if matched_words == 0
            else "low_confidence"
            if match_rate < low_confidence_threshold
            else "matched"
        )
        report = {
            "paragraph_index": sentence["paragraph_index"],
            "sentence_index": sentence["sentence_index"],
            "text": " ".join(sentence["words"]),
            "total_words": total_words,
            "matched_words": matched_words,
            "match_rate": round(match_rate, 4),
            "status": status,
        }
        sentence_reports.append(report)

        paragraph = paragraphs[sentence["paragraph_index"]]
        paragraph["total_words"] += total_words
        paragraph["matched_words"] += matched_words
        paragraph["sentence_count"] += 1

    paragraph_reports: list[dict[str, Any]] = []
    for paragraph_index, paragraph in paragraphs.items():
        match_rate = (
            paragraph["matched_words"] / paragraph["total_words"]
            if paragraph["total_words"]
            else 0.0
        )
        status = (
            "missing"
            if paragraph["matched_words"] == 0
            else "low_confidence"
            if match_rate < low_confidence_threshold
            else "matched"
        )
        paragraph_reports.append(
            {
                "paragraph_index": paragraph_index,
                "sentence_count": paragraph["sentence_count"],
                "total_words": paragraph["total_words"],
                "matched_words": paragraph["matched_words"],
                "match_rate": round(match_rate, 4),
                "status": status,
            }
        )

    return {
        "lesson": lesson_folder.name,
        "reference_word_count": len(list_ref),
        "whisper_word_count": len(whisper_words),
        "sentences": sentence_reports,
        "paragraphs": paragraph_reports,
    }


def print_flags(lesson_report: dict[str, Any]) -> None:
    flagged_sentences = [
        item for item in lesson_report["sentences"] if item["status"] != "matched"
    ]
    if not flagged_sentences:
        print(f"{lesson_report['lesson']}: all sentences matched")
        return

    print(f"\n{lesson_report['lesson']}")
    for item in flagged_sentences:
        print(
            f"  {item['status'].upper()} | paragraph {item['paragraph_index']}, "
            f"sentence {item['sentence_index']} | "
            f"{item['matched_words']}/{item['total_words']} words "
            f"({item['match_rate']:.0%})"
        )
        print(f"    {item['text']}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Find real-text sentences that Whisper did not match."
    )
    parser.add_argument("--input-root", type=Path, default=DEFAULT_INPUT_ROOT)
    parser.add_argument(
        "--low-confidence-threshold",
        type=float,
        default=0.5,
        help="Flag a sentence below this matched-word rate (default: 0.5).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Path for the JSON report. Defaults to missing_text_report.json in input root.",
    )
    args = parser.parse_args()

    if not 0 <= args.low_confidence_threshold <= 1:
        parser.error("--low-confidence-threshold must be between 0 and 1.")
    if not args.input_root.is_dir():
        parser.error(f"Input folder not found: {args.input_root}")

    reports: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    for lesson_folder in sorted(path for path in args.input_root.iterdir() if path.is_dir()):
        required_files = [lesson_folder / "text.txt", lesson_folder / "raw_timestamp.json"]
        missing = [path.name for path in required_files if not path.is_file()]
        if missing:
            skipped.append({"lesson": lesson_folder.name, "reason": f"Missing: {', '.join(missing)}"})
            continue

        lesson_report = build_lesson_report(
            lesson_folder, args.low_confidence_threshold
        )
        reports.append(lesson_report)
        print_flags(lesson_report)

    output_path = args.output or args.input_root / DEFAULT_OUTPUT_NAME
    output = {
        "input_root": str(args.input_root),
        "low_confidence_threshold": args.low_confidence_threshold,
        "lessons": reports,
        "skipped": skipped,
    }
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(output, file, ensure_ascii=False, indent=2)

    print(f"\nSaved report: {output_path}")
    if skipped:
        print(f"Skipped lessons: {len(skipped)}")


if __name__ == "__main__":
    main()
