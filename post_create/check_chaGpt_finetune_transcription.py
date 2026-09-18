"""Check every cleaned lesson transcript against its raw transcript."""

from __future__ import annotations

import difflib
import re
import sys
import unicodedata
from pathlib import Path
# C:\Users\PC\Desktop\kaggle\whisper\en\English Stories\lessons

REPOSITORY_DIR = Path(__file__).resolve().parent.parent
LESSONS_DIR = (
    REPOSITORY_DIR / "en" / "English Stories" / "lessons"
)
RAW_FILENAME = "raw_text.txt"
NEW_FILENAME = "text.txt"

# Bracketed transcript labels such as [Music] and [Applause] are artifacts rather
# than story words, so they do not participate in the comparison.
TRANSCRIPT_ARTIFACT = re.compile(r"\[[^\[\]\r\n]*\]")
APOSTROPHES = {"'", "\N{RIGHT SINGLE QUOTATION MARK}"}
CONTEXT_WORDS = 5
MAX_CHANGED_WORDS = 30


def normalize_words(text: str) -> list[str]:
    """Return comparable words, ignoring case, punctuation, and whitespace."""
    text = TRANSCRIPT_ARTIFACT.sub(" ", unicodedata.normalize("NFKC", text))

    normalized_characters: list[str] = []
    for character in text.casefold():
        if character.isalnum():
            normalized_characters.append(character)
        elif character in APOSTROPHES:
            # This makes "didn't" and "didnt" equivalent while retaining one word.
            continue
        else:
            # Punctuation, symbols, spaces, and paragraph breaks are separators.
            normalized_characters.append(" ")

    return "".join(normalized_characters).split()


def format_words(words: list[str]) -> str:
    if not words:
        return "(nothing)"
    if len(words) <= MAX_CHANGED_WORDS:
        return " ".join(words)

    half = MAX_CHANGED_WORDS // 2
    omitted_count = len(words) - (half * 2)
    return (
        f"{' '.join(words[:half])} ... "
        f"[{omitted_count} word(s) omitted] ... {' '.join(words[-half:])}"
    )


def format_location(start: int, end: int) -> str:
    if start == end:
        return f"position {start + 1}"
    if end == start + 1:
        return f"word {start + 1}"
    return f"words {start + 1}-{end}"


def context(words: list[str], start: int, end: int) -> str:
    context_start = max(0, start - CONTEXT_WORDS)
    context_end = min(len(words), end + CONTEXT_WORDS)
    before = " ".join(words[context_start:start])
    changed = format_words(words[start:end])
    after = " ".join(words[end:context_end])

    parts = [part for part in (before, f"[[{changed}]]", after) if part]
    return " ".join(parts)


def check_lesson(lesson_dir: Path) -> tuple[str, int]:
    """Print one lesson's result and return (status, difference count)."""
    raw_text_path = lesson_dir / RAW_FILENAME
    new_text_path = lesson_dir / NEW_FILENAME

    missing_files = [
        path.name for path in (raw_text_path, new_text_path) if not path.is_file()
    ]
    if missing_files:
        print(f"ERROR: Missing {', '.join(missing_files)}")
        return "ERROR", 0

    try:
        raw_text = raw_text_path.read_text(encoding="utf-8-sig")
        new_text = new_text_path.read_text(encoding="utf-8-sig")
    except OSError as error:
        print(f"ERROR: Could not read an input file: {error}")
        return "ERROR", 0

    raw_words = normalize_words(raw_text)
    new_words = normalize_words(new_text)

    if not raw_words:
        print(f"ERROR: {RAW_FILENAME} contains no words.")
        return "ERROR", 0
    if not new_words:
        print(
            f"EMPTY: {NEW_FILENAME} contains no words; "
            f"{RAW_FILENAME} contains {len(raw_words)} normalized words."
        )
        return "EMPTY", 1

    matcher = difflib.SequenceMatcher(None, raw_words, new_words, autojunk=False)
    differences = [opcode for opcode in matcher.get_opcodes() if opcode[0] != "equal"]

    print(f"Raw transcript:   {len(raw_words)} normalized words")
    print(f"Cleaned text:     {len(new_words)} normalized words")

    if not differences:
        print("PASS: The normalized word sequences are identical.")
        return "PASS", 0

    print(f"REVIEW: Found {len(differences)} word-level difference group(s).")
    print()

    for number, (operation, raw_start, raw_end, new_start, new_end) in enumerate(
        differences, start=1
    ):
        labels = {
            "replace": "REPLACED",
            "delete": "REMOVED FROM CLEANED TEXT",
            "insert": "ADDED TO CLEANED TEXT",
        }
        print(f"{number}. {labels[operation]}")
        print(
            f"   Raw {format_location(raw_start, raw_end)}: "
            f"{format_words(raw_words[raw_start:raw_end])}"
        )
        print(
            f"   New {format_location(new_start, new_end)}: "
            f"{format_words(new_words[new_start:new_end])}"
        )
        print(f"   Raw context: {context(raw_words, raw_start, raw_end)}")
        print(f"   New context: {context(new_words, new_start, new_end)}")
        print()

    return "REVIEW", len(differences)


def main() -> int:
    if not LESSONS_DIR.is_dir():
        print(f"Lessons directory does not exist: {LESSONS_DIR}", file=sys.stderr)
        return 2

    lesson_dirs = sorted(
        (path for path in LESSONS_DIR.iterdir() if path.is_dir()),
        key=lambda path: path.name.casefold(),
    )
    if not lesson_dirs:
        print(f"No lesson folders found in: {LESSONS_DIR}", file=sys.stderr)
        return 2

    results: list[tuple[str, str, int]] = []
    for lesson_number, lesson_dir in enumerate(lesson_dirs, start=1):
        print("=" * 80)
        print(f"Lesson {lesson_number}/{len(lesson_dirs)}: {lesson_dir.name}")
        print("=" * 80)
        status, difference_count = check_lesson(lesson_dir)
        results.append((lesson_dir.name, status, difference_count))
        print()

    pass_count = sum(status == "PASS" for _, status, _ in results)
    review_count = sum(status == "REVIEW" for _, status, _ in results)
    empty_count = sum(status == "EMPTY" for _, status, _ in results)
    error_count = sum(status == "ERROR" for _, status, _ in results)
    total_differences = sum(count for _, _, count in results)
    name_width = max(len("LESSON"), *(len(name) for name, _, _ in results))

    print("=" * 80)
    print("OVERALL SUMMARY")
    print("=" * 80)
    print(f"{'LESSON':<{name_width}}  STATUS  DIFFERENCE GROUPS")
    print(f"{'-' * name_width}  ------  -----------------")
    for name, status, difference_count in results:
        print(f"{name:<{name_width}}  {status:<6}  {difference_count}")

    print()
    print(f"Lessons checked:        {len(results)}")
    print(f"Passed:                 {pass_count}")
    print(f"Need review:            {review_count}")
    print(f"Empty cleaned files:    {empty_count}")
    print(f"Errors:                 {error_count}")
    print(f"Total difference groups: {total_differences}")

    if error_count:
        print("Result: ERROR - one or more lessons could not be checked.")
        return 2
    if review_count or empty_count:
        print("Result: REVIEW - inspect the differences shown above.")
        return 1

    print("Result: PASS - every normalized word sequence is identical.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# & C:\Users\PC\anaconda3\envs\yt311\python.exe `
#   "C:\Users\PC\Desktop\kaggle\whisper\post_create\check_chaGpt_finetune_transcription.py"