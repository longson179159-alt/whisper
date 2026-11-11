import argparse
import json
import sys
import os

# os.path.dirname
os.path.abspath(__file__)


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:  # Check whether the project root is already in Python's import path.
    sys.path.insert(0, PROJECT_ROOT)  # Add the project root to the beginning of the import path.

from helper import clean_word, get_lists_txt
from helper import Get_timestamp, group_by_para_or_sentence, nw_ref_match_flags


def get_lists_word_timestamp(word_timestamp_path):
    with open(word_timestamp_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict) or not isinstance(data.get("segments"), list):
        raise ValueError(f"Unsupported word timestamp format in {word_timestamp_path}")

    whisper_wordtimestamp = []
    whisper = []

    for segment in data["segments"]:
        words = segment.get("words")
        if not isinstance(words, list):
            raise ValueError(
                f"A segment has no word timestamps in {word_timestamp_path}. "
                "Run Whisper with word_timestamps=True."
            )

        for item in words:
            if not all(key in item for key in ("word", "start", "end")):
                raise ValueError(f"Invalid word timestamp entry in {word_timestamp_path}: {item}")

            word = clean_word(item["word"])
            if not word:
                continue

            start = item["start"]
            end = item["end"]
            if start > end:
                raise ValueError(
                    f"Word timestamp starts after it ends in {word_timestamp_path}: {item}"
                )
            if whisper_wordtimestamp and start < whisper_wordtimestamp[-1]["start"]:
                raise ValueError(f"Word timestamps are not chronological in {word_timestamp_path}")

            whisper.append(word)
            whisper_wordtimestamp.append(
                {
                    "word": word,
                    "start": start,
                    "end": end,
                }
            )

    if not whisper_wordtimestamp:
        raise ValueError(f"No usable word timestamps found in {word_timestamp_path}")

    return whisper_wordtimestamp, whisper


def interpolate_missing_timestamps(timestamp_word_level):
    consecutive_nulls_idx = []
    i = 0

    while i < len(timestamp_word_level):
        start = i
        end = i
        if not timestamp_word_level[i]["has_timestamp"]:
            while i + 1 < len(timestamp_word_level) and not timestamp_word_level[i + 1]["has_timestamp"]:
                i += 1
                end = i
            consecutive_nulls_idx.append((start, end))
        i += 1

    for first_null, final_null in consecutive_nulls_idx:
        if first_null > 0 and final_null < len(timestamp_word_level) - 1:
            start_time = timestamp_word_level[first_null - 1]["end"]
            end_time = timestamp_word_level[final_null + 1]["start"]
            number_nulls = final_null - first_null + 1
            gap = (end_time - start_time) / number_nulls

            for j in range(number_nulls):
                word_obj = timestamp_word_level[first_null + j]
                word_obj["has_timestamp"] = True
                word_obj["start"] = round(start_time + j * gap, 2)
                word_obj["end"] = round(start_time + (j + 1) * gap, 2)

    return timestamp_word_level


def build_standard_timestamp(txt_path, word_timestamp_path):
    list_ref, list_id = get_lists_txt(txt_path)
    whisper_wordtimestamp, whisper = get_lists_word_timestamp(word_timestamp_path)
    needleman_result = nw_ref_match_flags(list_ref, whisper)

    timestamp_word_level = []
    for i, item in enumerate(list_id):
        word, p_idx, s_idx, _idx_in_s = item
        matched_flag = needleman_result[i][1]
        matched_whisper_idx = needleman_result[i][2]

        if matched_flag == 1:
            ts = whisper_wordtimestamp[matched_whisper_idx]
            timestamp_word_level.append(
                {
                    "word": word,
                    "p_idx": p_idx,
                    "s_idx": s_idx,
                    "has_timestamp": True,
                    "start": ts["start"],
                    "end": ts["end"],
                }
            )
        else:
            timestamp_word_level.append(
                {
                    "word": word,
                    "p_idx": p_idx,
                    "s_idx": s_idx,
                    "has_timestamp": False,
                    "start": None,
                    "end": None,
                }
            )

    timestamp_word_level = interpolate_missing_timestamps(timestamp_word_level)

    timestamp_word_level_group_by_para = group_by_para_or_sentence(timestamp_word_level, "p_idx")
    timestamp_word_level_group_para_sentence = [
        group_by_para_or_sentence(item, "s_idx") for item in timestamp_word_level_group_by_para
    ]

    timestamp_result = [Get_timestamp(item) for item in timestamp_word_level_group_para_sentence]

    flattened_result = []
    for paragraph in timestamp_result:
        for sentence in paragraph:
            flattened_result.append(
                {
                    "start": sentence["start"],
                    "end": sentence["end"],
                    "text": sentence["text"],
                    "ts_idx": len(flattened_result),
                }
            )

    return flattened_result


def find_matching_file(folder, suffix):
    matches = sorted(
        os.path.join(folder, file_name)
        for file_name in os.listdir(folder)
        if file_name.endswith(suffix)
    )
    if not matches:
        return None
    if len(matches) > 1:
        raise ValueError(f"Multiple files match *{suffix} in {folder}")
    return matches[0]


def process_word_timestamp(folder):
    txt_path = os.path.join(folder, "text.txt")
    word_timestamp_path = os.path.join(folder, "word_timestamp.json")

    if not os.path.isfile(txt_path):
        raise FileNotFoundError(f"Missing text.txt in {folder}")
    if not os.path.isfile(word_timestamp_path):
        raise FileNotFoundError(f"Missing word_timestamp.json in {folder}")

    output_name = 'timestamp.json'
    output_path = os.path.join(folder, output_name)

    standard_timestamp = build_standard_timestamp(txt_path, word_timestamp_path)
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(standard_timestamp, file, ensure_ascii=False, indent=2)

    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Create timestamp.json files from Whisper word timestamps."
    )
    parser.add_argument("folder_path", help="Folder containing the lesson folders")
    args = parser.parse_args()
    current_folder_path = os.path.abspath(os.path.join(PROJECT_ROOT, args.folder_path))

    created_files = []

    for folder_name in sorted(os.listdir(current_folder_path)):
        
        folder = os.path.join(current_folder_path, folder_name)
        if not os.path.isdir(folder):
            continue

        # debug
        # print(f"Processing folder: {folder_name}")
        created_files.append(process_word_timestamp(folder))

    for output_path in created_files:
        with open(output_path, "r", encoding="utf-8") as file:
            timestamps = json.load(file)

        null_timestamps = [
            timestamp
            for timestamp in timestamps
            if timestamp["start"] is None or timestamp["end"] is None
        ]

        if null_timestamps:
            lesson_name = os.path.basename(os.path.dirname(output_path))
            print(f"\n{lesson_name}: {len(null_timestamps)} timestamp(s) with null values")
            for timestamp in null_timestamps:
                print(timestamp)


if __name__ == "__main__":
    main()

# Example:
# python add_timestamp/add_timestamp.py "en/how_to_stop_worrying_and_start_living/lessons"
