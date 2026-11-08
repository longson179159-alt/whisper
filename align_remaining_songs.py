import argparse
import difflib
import hashlib
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LESSONS = ROOT / "en/US-UK 2/lessons"
SOURCES = ROOT / "en/US-UK 2/US_UK_2_timestamp_files"

SKIP_WRONG_LYRICS = {4, 9}
EXCLUDED_LINE_INDEXES = {
    2: {0, 1},
    6: {0, 14, 29, 30, 31, 32, 33},
    12: {0, 1, 2, 3, 4, 5, 7, 8, 9},
}


@dataclass
class LyricToken:
    value: str
    line_index: int


@dataclass
class TimedToken:
    value: str
    start: float
    end: float


def lesson_number(path: Path) -> int:
    return int(path.name.split(".", 1)[0])


def normalized_tokens(value: str) -> list[str]:
    return re.findall(r"[a-z]+(?:'[a-z]+)?", value.replace("’", "'").lower())


def simplified(value: str) -> str:
    value = value.replace("'", "")
    if value.endswith("ing") and len(value) > 4:
        return value[:-1]
    return value


def similarity(left: str, right: str) -> float:
    if left == right:
        return 3.0
    if simplified(left) == simplified(right):
        return 2.4
    ratio = difflib.SequenceMatcher(None, left, right).ratio()
    if ratio >= 0.82:
        return 1.0
    return -1.2


def clean_lyrics(path: Path) -> list[str]:
    cleaned = []
    skip_recommendations = False
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if line == "You might also like":
            skip_recommendations = True
            continue
        is_header = line.startswith("[") and line.endswith("]")
        if skip_recommendations and is_header:
            skip_recommendations = False
        if skip_recommendations or not line or is_header:
            continue
        if re.fullmatch(r"\d*Embed", line):
            continue
        if line.lower().startswith(("source:", "songwriters:", "lyrics ©", "lyrics �")):
            continue
        cleaned.append(line)
    return cleaned


def selected_lyrics(lesson: Path) -> list[str]:
    lines = clean_lyrics(lesson / "lyrics.txt")
    excluded = EXCLUDED_LINE_INDEXES.get(lesson_number(lesson), set())
    return [line for index, line in enumerate(lines) if index not in excluded]


def lyric_tokens(lines: list[str]) -> list[LyricToken]:
    result = []
    for line_index, line in enumerate(lines):
        result.extend(LyricToken(value, line_index) for value in normalized_tokens(line))
    return result


def source_tokens(path: Path) -> list[TimedToken]:
    source = json.loads(path.read_text(encoding="utf-8-sig"))
    result = []
    for segment in source:
        for word in segment.get("words", []):
            values = normalized_tokens(word.get("word", ""))
            if not values:
                continue
            duration = max(0.01, word["end"] - word["start"])
            for offset, value in enumerate(values):
                start = word["start"] + duration * offset / len(values)
                end = word["start"] + duration * (offset + 1) / len(values)
                result.append(TimedToken(value, start, end))
    return result


def align(raw: list[TimedToken], lyrics: list[LyricToken]) -> tuple[list[int | None], list[bool]]:
    gap = -1.0
    rows = len(raw) + 1
    cols = len(lyrics) + 1
    trace = [bytearray(cols) for _ in range(rows)]
    previous = [gap * column for column in range(cols)]
    for column in range(1, cols):
        trace[0][column] = 2
    for row in range(1, rows):
        current = [gap * row] + [0.0] * (cols - 1)
        trace[row][0] = 1
        for column in range(1, cols):
            diagonal = previous[column - 1] + similarity(raw[row - 1].value, lyrics[column - 1].value)
            delete_raw = previous[column] + gap
            insert_lyric = current[column - 1] + gap
            best = max(diagonal, delete_raw, insert_lyric)
            current[column] = best
            if best == diagonal:
                trace[row][column] = 0
            elif best == delete_raw:
                trace[row][column] = 1
            else:
                trace[row][column] = 2
        previous = current

    mapping: list[int | None] = [None] * len(lyrics)
    anchored = [False] * len(lyrics)
    row = len(raw)
    column = len(lyrics)
    while row or column:
        direction = trace[row][column]
        if row and column and direction == 0:
            mapping[column - 1] = row - 1
            if similarity(raw[row - 1].value, lyrics[column - 1].value) > 0:
                anchored[column - 1] = True
            row -= 1
            column -= 1
        elif row and (not column or direction == 1):
            row -= 1
        else:
            column -= 1
    return mapping, anchored


def longest_unanchored(mapping: list[int | None]) -> int:
    longest = current = 0
    for item in mapping:
        if item is None:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def line_anchor_counts(tokens: list[LyricToken], mapping: list[int | None], line_count: int) -> list[int]:
    counts = [0] * line_count
    for token, raw_index in zip(tokens, mapping):
        if raw_index is not None:
            counts[token.line_index] += 1
    return counts


def maximum_inferred_rate(raw: list[TimedToken], mapping: list[int | None]) -> float:
    maximum = 0.0
    index = 0
    while index < len(mapping):
        if mapping[index] is not None:
            index += 1
            continue
        start = index
        while index < len(mapping) and mapping[index] is None:
            index += 1
        count = index - start
        previous_raw = mapping[start - 1] if start else None
        next_raw = mapping[index] if index < len(mapping) else None
        if previous_raw is None and next_raw is not None:
            seconds = raw[next_raw].start
        elif previous_raw is not None and next_raw is None:
            seconds = max(0.0, raw[-1].end - raw[previous_raw].end)
        elif previous_raw is not None and next_raw is not None:
            seconds = max(0.0, raw[next_raw].start - raw[previous_raw].end)
        else:
            seconds = 0.0
        maximum = max(maximum, count / max(seconds, 0.01))
    return maximum


def audit_lesson(lesson: Path) -> dict:
    lines = selected_lyrics(lesson)
    lyrics = lyric_tokens(lines)
    raw = source_tokens(SOURCES / f"{lesson.name}.json")
    mapping, anchor_flags = align(raw, lyrics)
    anchored = sum(anchor_flags)
    counts = line_anchor_counts(lyrics, mapping, len(lines))
    return {
        "lesson": lesson,
        "lines": lines,
        "lyrics": lyrics,
        "raw": raw,
        "mapping": mapping,
        "anchor_flags": anchor_flags,
        "coverage": anchored / len(lyrics) if lyrics else 0,
        "longest_gap": longest_unanchored([index if flag else None for index, flag in enumerate(anchor_flags)]),
        "unanchored_lines": sum(count == 0 for count in counts),
        "unanchored_line_indexes": [index for index, count in enumerate(counts) if count == 0],
        "max_inferred_rate": maximum_inferred_rate(raw, mapping),
    }


def inferred_token_times(raw: list[TimedToken], mapping: list[int | None]) -> list[tuple[float, float]]:
    result: list[tuple[float, float] | None] = [None] * len(mapping)
    for index, raw_index in enumerate(mapping):
        if raw_index is not None:
            result[index] = (raw[raw_index].start, raw[raw_index].end)

    index = 0
    while index < len(result):
        if result[index] is not None:
            index += 1
            continue
        start = index
        while index < len(result) and result[index] is None:
            index += 1
        count = index - start
        previous = result[start - 1] if start else None
        following = result[index] if index < len(result) else None
        if previous is not None and following is not None:
            left = (previous[0] + previous[1]) / 2
            right = (following[0] + following[1]) / 2
            if right <= left:
                right = left + 0.02 * (count + 1)
        elif following is not None:
            right = following[0]
            left = max(0.0, right - 0.38 * count)
        elif previous is not None:
            left = previous[1]
            right = max(left + 0.38 * count, raw[-1].end)
        else:
            left = 0.0
            right = max(0.38 * count, raw[-1].end)
        step = (right - left) / (count + 1)
        width = max(0.01, min(0.25, step * 0.8))
        for offset in range(count):
            midpoint = left + step * (offset + 1)
            result[start + offset] = (max(0.0, midpoint - width / 2), midpoint + width / 2)

    return [item for item in result if item is not None]


def build_segments(result: dict) -> list[dict]:
    line_token_indexes: list[list[int]] = [[] for _ in result["lines"]]
    for token_index, token in enumerate(result["lyrics"]):
        line_token_indexes[token.line_index].append(token_index)

    nominal: list[dict | None] = []
    for line_index, line in enumerate(result["lines"]):
        indexes = line_token_indexes[line_index]
        mapped = [
            (result["mapping"][index], result["anchor_flags"][index])
            for index in indexes if result["mapping"][index] is not None
        ]
        if not mapped:
            nominal.append(None)
            continue
        clusters: list[list[tuple[int, bool]]] = [[]]
        for raw_index, anchored in mapped:
            if clusters[-1]:
                previous_raw = clusters[-1][-1][0]
                gap = result["raw"][raw_index].start - result["raw"][previous_raw].end
                if gap > 2.0:
                    clusters.append([])
            clusters[-1].append((raw_index, anchored))
        cluster = max(
            clusters,
            key=lambda items: (sum(anchored for _, anchored in items), len(items)),
        )
        start = min(result["raw"][raw_index].start for raw_index, _ in cluster)
        end = max(result["raw"][raw_index].end for raw_index, _ in cluster)
        maximum_duration = max(2.0, len(indexes) * 0.5)
        if end - start > maximum_duration:
            midpoints = sorted(
                (result["raw"][raw_index].start + result["raw"][raw_index].end) / 2
                for raw_index, _ in cluster
            )
            center = midpoints[len(midpoints) // 2]
            start = max(start, center - maximum_duration / 2)
            end = min(end, start + maximum_duration)
        nominal.append({"start": start, "end": end, "text": line})

    index = 0
    while index < len(nominal):
        if nominal[index] is not None:
            index += 1
            continue
        start_index = index
        while index < len(nominal) and nominal[index] is None:
            index += 1
        count = index - start_index
        left = nominal[start_index - 1]["end"] if start_index else 0.0
        right = nominal[index]["start"] if index < len(nominal) else result["raw"][-1].end
        if right <= left:
            right = left + 0.02 * count
        weights = [max(1, len(line_token_indexes[item])) for item in range(start_index, index)]
        desired = [max(0.6, min(4.5, weight * 0.35)) for weight in weights]
        available = right - left
        scale = min(1.0, available / sum(desired))
        durations = [duration * scale for duration in desired]
        cursor = left + max(0.0, (available - sum(durations)) / 2)
        for offset, duration in enumerate(durations):
            nominal[start_index + offset] = {
                "start": cursor,
                "end": cursor + duration,
                "text": result["lines"][start_index + offset],
            }
            cursor += duration

    segments = []
    for item in nominal:
        start = round(item["start"], 3)
        end = round(max(item["end"], start + 0.01), 3)
        if segments and start < segments[-1]["end"]:
            boundary = round((start + segments[-1]["end"]) / 2, 3)
            if boundary > segments[-1]["start"] + 0.01 and boundary < end - 0.01:
                segments[-1]["end"] = boundary
                start = boundary
            else:
                segments[-1]["text"] += " " + item["text"]
                segments[-1]["end"] = max(segments[-1]["end"], end)
                continue
        segments.append({"start": start, "end": end, "text": item["text"]})

    for index, segment in enumerate(segments):
        segment["ts_idx"] = index
    return segments


def apply_lesson(result: dict) -> None:
    lesson = result["lesson"]
    raw_timestamp = lesson / "raw_timestamp.json"
    raw_text = lesson / "raw_text.txt"
    output_text = lesson / "text.txt"
    backup = lesson / "raw_timestamp.before_lyrics_alignment.json"
    if backup.exists():
        raise RuntimeError(f"Backup already exists: {backup}")
    raw_text_hash = hashlib.sha256(raw_text.read_bytes()).hexdigest()
    segments = build_segments(result)
    expected_words = [token.value for token in result["lyrics"]]
    actual_words = normalized_tokens(" ".join(segment["text"] for segment in segments))
    if actual_words != expected_words:
        raise RuntimeError(f"Generated words do not match selected lyrics for {lesson.name}")
    if not all(a["end"] <= b["start"] for a, b in zip(segments, segments[1:])):
        raise RuntimeError(f"Non-chronological timestamps for {lesson.name}")
    shutil.copy2(raw_timestamp, backup)
    raw_timestamp.write_text(
        json.dumps(segments, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    output_text.write_text(
        "".join(f"{segment['text']}\n" for segment in segments),
        encoding="utf-8",
    )
    if hashlib.sha256(raw_text.read_bytes()).hexdigest() != raw_text_hash:
        raise RuntimeError(f"raw_text.txt changed unexpectedly for {lesson.name}")
    if json.loads(raw_timestamp.read_text(encoding="utf-8")) != segments:
        raise RuntimeError(f"Timestamp verification failed for {lesson.name}")
    print(f"   APPLIED segments={len(segments)} backup={backup.name}")


def validate_lesson(result: dict) -> None:
    lesson = result["lesson"]
    raw_timestamp = lesson / "raw_timestamp.json"
    output_text = lesson / "text.txt"
    backup = lesson / "raw_timestamp.before_lyrics_alignment.json"
    segments = json.loads(raw_timestamp.read_text(encoding="utf-8"))
    expected_words = [token.value for token in result["lyrics"]]
    timestamp_words = normalized_tokens(" ".join(segment["text"] for segment in segments))
    expected_text = "".join(f"{segment['text']}\n" for segment in segments)
    actual_text = output_text.read_text(encoding="utf-8")
    checks = {
        "backup": backup.exists(),
        "words": timestamp_words == expected_words,
        "text": actual_text == expected_text,
        "indices": [segment["ts_idx"] for segment in segments] == list(range(len(segments))),
        "chronological": all(a["end"] <= b["start"] for a, b in zip(segments, segments[1:])),
    }
    if not all(checks.values()):
        raise RuntimeError(f"Validation failed for {lesson.name}: {checks}")
    print(f"   VALIDATED segments={len(segments)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--details", action="store_true")
    args = parser.parse_args()
    for lesson in sorted((path for path in LESSONS.iterdir() if path.is_dir()), key=lesson_number):
        number = lesson_number(lesson)
        if number == 1:
            continue
        if number in SKIP_WRONG_LYRICS:
            print(f"{number:02d} SKIPPED wrong lyrics file")
            continue
        result = audit_lesson(lesson)
        preview_segments = build_segments(result)
        durations = [segment["end"] - segment["start"] for segment in preview_segments]
        print(
            f"{number:02d} coverage={result['coverage']:.3f} "
            f"longest_gap={result['longest_gap']:3d} "
            f"unanchored_lines={result['unanchored_lines']:2d}/{len(result['lines'])} "
            f"max_rate={result['max_inferred_rate']:5.1f}/s "
            f"segments={len(preview_segments):2d} "
            f"duration={min(durations):.2f}-{max(durations):.2f}s "
            f"line_indexes={result['unanchored_line_indexes']}"
        )
        for segment in preview_segments:
            if segment["end"] - segment["start"] > 10:
                print(
                    f"   LONG {segment['start']:.2f}-{segment['end']:.2f} "
                    f"({segment['end'] - segment['start']:.2f}s) {segment['text'][:70]!r}"
                )
        if args.apply:
            if result["coverage"] < 0.70:
                raise RuntimeError(f"Refusing low-confidence lesson {number}: {result['coverage']:.3f}")
            apply_lesson(result)
        if args.validate:
            validate_lesson(result)
        if args.details and result["unanchored_line_indexes"]:
            for line_index in result["unanchored_line_indexes"]:
                token_indexes = [
                    index for index, token in enumerate(result["lyrics"])
                    if token.line_index == line_index
                ]
                first = token_indexes[0]
                last = token_indexes[-1]
                previous = next(
                    (result["mapping"][index] for index in range(first - 1, -1, -1)
                     if result["mapping"][index] is not None),
                    None,
                )
                following = next(
                    (result["mapping"][index] for index in range(last + 1, len(result["mapping"]))
                     if result["mapping"][index] is not None),
                    None,
                )
                previous_time = result["raw"][previous].end if previous is not None else 0.0
                following_time = result["raw"][following].start if following is not None else result["raw"][-1].end
                preview = result["lines"][line_index][:70]
                print(f"   line={line_index:02d} window={previous_time:.2f}-{following_time:.2f} {preview!r}")
        if args.details and number in {6, 12, 13, 15}:
            print("   CLEANED LINES")
            for line_index, line in enumerate(result["lines"]):
                print(f"   {line_index:02d}: {line}")


if __name__ == "__main__":
    main()
