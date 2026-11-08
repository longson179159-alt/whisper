import difflib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LESSONS = ROOT / "en/US-UK 2/lessons"


def lesson_number(path: Path) -> int:
    return int(path.name.split(".", 1)[0])


def tokens(value: str) -> list[str]:
    return re.findall(r"[a-z]+(?:'[a-z]+)?", value.replace("’", "'").lower())


def longest_unmatched_lyric_run(matcher: difflib.SequenceMatcher) -> int:
    longest = 0
    previous_lyric_end = 0
    for block in matcher.get_matching_blocks():
        longest = max(longest, block.b - previous_lyric_end)
        previous_lyric_end = block.b + block.size
    return longest


def clean_lines(path: Path) -> tuple[list[str], list[str], list[str]]:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    cleaned = []
    headers = []
    removed = []
    skip_recommendations = False
    for raw in lines:
        line = raw.strip()
        if line == "You might also like":
            skip_recommendations = True
            removed.append(line)
            continue
        is_header = line.startswith("[") and line.endswith("]")
        if skip_recommendations and is_header:
            skip_recommendations = False
        if skip_recommendations:
            if line:
                removed.append(line)
            continue
        if not line:
            continue
        if is_header:
            headers.append(line)
            continue
        if re.fullmatch(r"\d*Embed", line):
            removed.append(line)
            continue
        cleaned.append(line)
    return cleaned, headers, removed


for lesson in sorted((p for p in LESSONS.iterdir() if p.is_dir()), key=lesson_number):
    if lesson_number(lesson) == 1:
        continue
    lyric_lines, headers, removed = clean_lines(lesson / "lyrics.txt")
    raw = (lesson / "raw_text.txt").read_text(encoding="utf-8-sig")
    lyric_words = tokens(" ".join(lyric_lines))
    raw_words = tokens(raw)
    ratio = difflib.SequenceMatcher(None, raw_words, lyric_words, autojunk=False).ratio()
    source = ROOT / "en/US-UK 2/US_UK_2_timestamp_files" / f"{lesson.name}.json"
    source_data = json.loads(source.read_text(encoding="utf-8-sig"))
    has_word_times = all(isinstance(item.get("words"), list) for item in source_data)
    source_words = []
    for item in source_data:
        for word in item.get("words", []):
            source_words.extend(tokens(word.get("word", "")))
    matcher = difflib.SequenceMatcher(None, source_words, lyric_words, autojunk=False)
    matched = sum(block.size for block in matcher.get_matching_blocks())
    coverage = matched / len(lyric_words) if lyric_words else 0
    longest_gap = longest_unmatched_lyric_run(matcher)
    print(
        f"{lesson_number(lesson):02d} | raw={len(raw_words):4d} lyrics={len(lyric_words):4d} "
        f"ratio={ratio:.3f} exact_coverage={coverage:.3f} longest_gap={longest_gap:3d} "
        f"lines={len(lyric_lines):3d} headers={len(headers):2d} "
        f"removed={len(removed):2d} word_times={has_word_times} text_exists={(lesson / 'text.txt').exists()}"
    )
    if removed:
        print(f"   removed_preview={removed[:5]}")
    suspicious = [line for line in lyric_lines if line.lower() in {"lyrics", "translations"}]
    if suspicious:
        print(f"   suspicious={suspicious}")
