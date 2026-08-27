import json
import os


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LESSONS_PATH = os.path.join(PROJECT_ROOT, "youtube_data", "short story for learning english", "lessons")

list_number_lessons = []
lesson_paths = []

for folder_name in sorted(os.listdir(LESSONS_PATH)):
    lesson_path = os.path.join(LESSONS_PATH, folder_name)
    if not os.path.isdir(lesson_path):
        continue

    description_path = os.path.join(lesson_path, "description.json")
    if not os.path.exists(description_path):
        raise FileNotFoundError(f"{folder_name}: no description.json")

    with open(description_path, "r", encoding="utf-8") as f:
        description = json.load(f)
        if not isinstance(description, dict):
            raise ValueError(f"{folder_name}: description.json is not a JSON object")
        lesson_number = description.get("lesson_number")

        if not isinstance(lesson_number, int):
            raise ValueError(f"{folder_name}: lesson_number is missing or invalid")

        # check if the folder name already starts with a number
        if len(folder_name) >= 6 and folder_name[:3].isdigit() and folder_name[3:6] == " - ":
            print(f"{folder_name}: folder already has a number prefix, skipping")
            continue

    new_folder_name = f"{lesson_number:03d} - {folder_name}"

    new_lesson_path = os.path.join(LESSONS_PATH, new_folder_name)
    os.rename(lesson_path, new_lesson_path)
    print(f"Renamed folder: {folder_name} -> {new_folder_name}")