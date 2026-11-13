import argparse
import json
import os

from helper import clean_word, get_lists_txt
from helper import Get_timestamp, group_by_para_or_sentence, nw_ref_match_flags


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_lists_raw_timestamp(raw_timestamp_path):
    """Estimate word timings by evenly dividing each Whisper segment."""
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

        if not list_words:
            continue

        gap = (end_sentence - start_sentence) / len(list_words)

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
            while (
                i + 1 < len(timestamp_word_level)
                and not timestamp_word_level[i + 1]["has_timestamp"]
            ):
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

    timestamp_word_level_group_by_para = group_by_para_or_sentence(
        timestamp_word_level, "p_idx"
    )
    timestamp_word_level_group_para_sentence = [
        group_by_para_or_sentence(item, "s_idx")
        for item in timestamp_word_level_group_by_para
    ]

    timestamp_result = [
        Get_timestamp(item)
        for item in timestamp_word_level_group_para_sentence
    ]

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


def process_raw_timestamp(folder):
    txt_path = os.path.join(folder, "text.txt")
    raw_timestamp_path = os.path.join(folder, "raw_timestamp.json")

    if not os.path.isfile(txt_path):
        raise FileNotFoundError(f"Missing text.txt in {folder}")
    if not os.path.isfile(raw_timestamp_path):
        raise FileNotFoundError(f"Missing raw_timestamp.json in {folder}")

    output_path = os.path.join(folder, "timestamp.json")
    standard_timestamp = build_standard_timestamp(txt_path, raw_timestamp_path)

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(standard_timestamp, file, ensure_ascii=False, indent=2)

    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Create timestamp.json files from raw_timestamp.json."
    )
    parser.add_argument("folder_path", help="Folder containing the lesson folders")
    args = parser.parse_args()

    current_folder_path = os.path.abspath(
        os.path.join(PROJECT_ROOT, args.folder_path)
    )
    if not os.path.isdir(current_folder_path):
        raise FileNotFoundError(
            f"Lesson parent folder does not exist: {current_folder_path}"
        )

    created_files = []

    for folder_name in sorted(os.listdir(current_folder_path)):
        folder = os.path.join(current_folder_path, folder_name)
        if not os.path.isdir(folder):
            continue

        created_files.append(process_raw_timestamp(folder))

    for output_path in created_files:
        with open(output_path, "r", encoding="utf-8") as file:
            timestamps = json.load(file)

        null_timestamps = [
            timestamp
            for timestamp in timestamps
            if timestamp["start"] is None or timestamp["end"] is None
        ]

        print(f"Created {output_path}")

        if null_timestamps:
            lesson_name = os.path.basename(os.path.dirname(output_path))
            print(
                f"{lesson_name}: "
                f"{len(null_timestamps)} timestamp(s) with null values"
            )
            for timestamp in null_timestamps:
                print(timestamp)


if __name__ == "__main__":
    main()


# Example:
# python add_timestamp/add_timesatmp_2.py "zh/course/lessons"
