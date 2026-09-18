"""Check that cleaning a transcript did not change its words or word order."""

from __future__ import annotations

import difflib
import re
import sys
import unicodedata
from pathlib import Path


RAW_TEXT_PATH = Path(
    r"C:\Users\PC\Desktop\kaggle\whisper\en\short story for learning english"
    r"\lessons\001 - Who is She Story\raw_text.txt"
)
NEW_TEXT_PATH = Path(
    r"C:\Users\PC\Desktop\kaggle\whisper\en\short story for learning english"
    r"\lessons\001 - Who is She Story\text.txt"
)

# Bracketed transcript labels such as [Music] and [Applause] are artifacts rather
# than story words, so they do not participate in the comparison.
TRANSCRIPT_ARTIFACT = re.compile(r"\[[^\[\]\r\n]*\]")
APOSTROPHES = {"'", "\N{RIGHT SINGLE QUOTATION MARK}"}
CONTEXT_WORDS = 5


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
    return " ".join(words) if words else "(nothing)"


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


def main() -> int:
    try:
        raw_text = RAW_TEXT_PATH.read_text(encoding="utf-8-sig")
        new_text = NEW_TEXT_PATH.read_text(encoding="utf-8-sig")
    except OSError as error:
        print(f"Could not read an input file: {error}", file=sys.stderr)
        return 2

    raw_words = normalize_words(raw_text)
    new_words = normalize_words(new_text)
    matcher = difflib.SequenceMatcher(None, raw_words, new_words, autojunk=False)
    differences = [opcode for opcode in matcher.get_opcodes() if opcode[0] != "equal"]

    print(f"Raw transcript:   {len(raw_words)} normalized words")
    print(f"Cleaned text:     {len(new_words)} normalized words")

    if not differences:
        print("PASS: The normalized word sequences are identical.")
        return 0

    print(f"FAIL: Found {len(differences)} word-level difference group(s).")
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

    print("Review every difference above. Exit status: 1")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
