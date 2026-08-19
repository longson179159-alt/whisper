import json
import sys
import os

# os.path.dirname
os.path.abspath(__file__)


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


CURRENT_FOLDER = '6_minute_bbc/lessons/'  # Name of the folder containing the text and raw timestamp files.
CURRENT_FOLDER_PATH = os.path.join(PROJECT_ROOT, 'en', CURRENT_FOLDER)  # Path to the folder containing the text and raw timestamp files.

if PROJECT_ROOT not in sys.path:  # Check whether the project root is already in Python's import path.
    sys.path.insert(0, PROJECT_ROOT)  # Add the project root to the beginning of the import path.

from helper import clean_word, get_lists_txt
from helper import Get_timestamp, group_by_para_or_sentence, nw_ref_match_flags


def get_lists_raw_timestamp(raw_timestamp_path):
    with open(raw_timestamp_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    if isinstance(data, dict):
        segments = data.get("segments", [])
    elif isinstance(data, list):
        segments = data
    else:
        raise ValueError(f"Unsupported timestamp format in {raw_timestamp_path}")

    whisper_wordtimestamp = []
    whisper = []

    for item in segments:
        start_sentence = item["start"]
        end_sentence = item["end"]
        list_words = [clean_word(word) for word in item["text"].split()]
        list_words = [word for word in list_words if word]

        if list_words:
            gap = (end_sentence - start_sentence) / len(list_words)
        else:
            gap = 1

        for i, word in enumerate(list_words):
            whisper.append(word)
            whisper_wordtimestamp.append(
                {
                    "word": word,
                    "start": round(start_sentence + gap * i, 2),
                    "end": round(start_sentence + gap * (i + 1), 2),
                }
            )

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


def build_standard_timestamp(txt_path, raw_timestamp_path):
    list_ref, list_id = get_lists_txt(txt_path)
    whisper_wordtimestamp, whisper = get_lists_raw_timestamp(raw_timestamp_path)
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


def process_raw_timestamp(folder):
    txt_path = os.path.join(folder, "text.txt")
    raw_timestamp_path = os.path.join(folder, "raw_timestamp.json")
    
    if txt_path is None or raw_timestamp_path is None:
        raise FileNotFoundError(f"Missing txt or raw timestamp file in {folder}")

    output_name = 'timestamp.json'
    output_path = os.path.join(folder, output_name)

    standard_timestamp = build_standard_timestamp(txt_path, raw_timestamp_path)
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(standard_timestamp, file, ensure_ascii=False, indent=2)

    return output_path


def main():
    # sample_dir = CURRENT_FOLDER_PATH
    created_files = []

    for folder_name in sorted(os.listdir(CURRENT_FOLDER_PATH)):
        folder = os.path.join(CURRENT_FOLDER_PATH, folder_name)
        if not os.path.isdir(folder):
            continue
        created_files.append(process_raw_timestamp(folder))

    for output_path in created_files:
        print(f"Created {os.path.basename(output_path)}")


if __name__ == "__main__":
    main()
