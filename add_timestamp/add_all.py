from add_lesson import process_text
from add_timestamp import process_raw_timestamp
import argparse
import json
import os


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    parser = argparse.ArgumentParser(description="Create lesson.json and timestamp.json files.")
    parser.add_argument("folder_path", help="Folder containing the lesson folders")
    args = parser.parse_args()
    current_folder_path = os.path.abspath(os.path.join(PROJECT_ROOT, args.folder_path))

    created_files = []
    timestamp_files = []

    for folder_name in sorted(os.listdir(current_folder_path)):
        folder = os.path.join(current_folder_path, folder_name)

        if not os.path.isdir(folder):
            continue
        
        created_files.append(process_text(folder))
        timestamp_path = process_raw_timestamp(folder)
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
# python add_timestamp/add_all.py "en/how_to_stop_worrying_and_start_living/lessons"

