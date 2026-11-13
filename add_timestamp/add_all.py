from add_lesson import process_text
from add_timestamp import process_word_timestamp
from add_timesatmp_2 import process_raw_timestamp
import argparse
import json
import os


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    parser = argparse.ArgumentParser(description="Create lesson.json and timestamp.json files.")
    parser.add_argument("folder_path", help="Folder containing the lesson folders")
    parser.add_argument(
        "--timestamp-type",
        type=int,
        choices=(1, 2),
        required=True,
        help=(
            "Timestamp source: 1 = word_timestamp.json via add_timestamp.py; "
            "2 = raw_timestamp.json via add_timesatmp_2.py"
        ),
    )
    args = parser.parse_args()
    current_folder_path = os.path.abspath(os.path.join(PROJECT_ROOT, args.folder_path))

    timestamp_processor = (
        process_word_timestamp
        if args.timestamp_type == 1
        else process_raw_timestamp
    )

    created_files = []
    timestamp_files = []

    for folder_name in sorted(os.listdir(current_folder_path)):
        folder = os.path.join(current_folder_path, folder_name)

        if not os.path.isdir(folder):
            continue
        
        created_files.append(process_text(folder))
        timestamp_path = timestamp_processor(folder)
        created_files.append(timestamp_path)
        timestamp_files.append(timestamp_path)

    for output_path in created_files:
        print(f"Created {os.path.basename(output_path)}")

    for output_path in timestamp_files:
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
# Type 1: word_timestamp.json
# python add_timestamp/add_all.py "zh/course/lessons" --timestamp-type 1
#
# Type 2: raw_timestamp.json
# python add_timestamp/add_all.py "zh/course/lessons" --timestamp-type 2

