from add_lesson import process_raw_text
from add_timestamp import process_raw_timestamp
import argparse
import os


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    parser = argparse.ArgumentParser(description="Create lesson.json and timestamp.json files.")
    parser.add_argument("folder_path", help="Folder containing the lesson folders")
    args = parser.parse_args()
    current_folder_path = os.path.abspath(os.path.join(PROJECT_ROOT, args.folder_path))

    created_files = []
    # delete_files = []

    for folder_name in sorted(os.listdir(current_folder_path)):
        folder = os.path.join(current_folder_path, folder_name)

        if not os.path.isdir(folder):
            continue
        
        created_files.append(process_raw_text(folder))

        created_files.append(process_raw_timestamp(folder))

        # remove the raw text and timestamp files after processing
        # raw_text_path = os.path.join(folder, f"raw_text.txt")
        # raw_timestamp_path = os.path.join(folder, f"raw_timestamp.json")

     
    
    for output_path in created_files:
        print(f"Created {os.path.basename(output_path)}")


if __name__ == "__main__":
    main()

# Example:
# python add_timestamp/add_all.py "en/how_to_stop_worrying_and_start_living/lessons"

