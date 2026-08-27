import json
import os
# import sys
from helper import get_lists_from_text

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# C:\Users\PC\Desktop\whisper\youtube_data\gatsby_the_greate\lessons
# C:\Users\PC\Desktop\whisper\youtube_data\how_to_stop_worrying
# C:\Users\PC\Desktop\whisper\youtube_data\The_alchemist_chapters

CURRENT_FOLDER = 'The_alchemist_chapters/lessons/'
CURRENT_FOLDER_PATH = os.path.join(PROJECT_ROOT, 'youtube_data', CURRENT_FOLDER)  # Path to the folder containing the text and raw timestamp files.
def build_standard_text(text_path):
    with open(text_path, "r", encoding="utf-8") as file:
        text = file.read()

    list_ref, list_id = get_lists_from_text(text)
    return {
        "list_ref": list_ref,
        "list_id": list_id,
    }


def process_text(folder):

    text_path = os.path.join(folder, f"text.txt")

    if not os.path.exists(text_path):
        raise FileNotFoundError(f"Missing raw text file in {folder}")

    output_path = os.path.join(folder, "lesson.json")
    standard_text = build_standard_text(text_path)

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(standard_text, file, ensure_ascii=False, indent=2)

    return output_path


def main():
    # Get the path to the "sample" folder, which is located next to this Python file.
    # CURRENT_FOLDER_PATH

    # Store the paths of all files created by process_raw_text().
    created_files = []

    # Loop through every item (folder or file) inside the sample directory, in alphabetical order.
    for folder_name in sorted(os.listdir(CURRENT_FOLDER_PATH)):

        # Build the full path to the current item.
        folder = os.path.join(CURRENT_FOLDER_PATH, folder_name)

        # Skip this item if it is not a folder.
        if not os.path.isdir(folder):
            continue

        # Process this folder and save the output file path.
        created_files.append(process_text(folder))

    print(f"Successfully created {len(created_files)} lesson.json file(s).")

    # Print the name of every file that was created.
    # for output_path in created_files:

    #     # Display only the filename, not the full path.
    #     print(f"Created {os.path.basename(output_path)}")

if __name__ == "__main__":
    main()
