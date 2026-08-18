from add_lesson import process_raw_text
from add_timestamp import process_raw_timestamp
import os


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


CURRENT_FOLDER = 'listen_a_minute'
CURRENT_FOLDER_PATH = os.path.join(PROJECT_ROOT, 'en', CURRENT_FOLDER)  # Path to the folder containing the text and raw timestamp files.


def main():
  

    created_files = []
    # delete_files = []

    for folder_name in sorted(os.listdir(CURRENT_FOLDER_PATH)):
        folder = os.path.join(CURRENT_FOLDER_PATH, folder_name)

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

