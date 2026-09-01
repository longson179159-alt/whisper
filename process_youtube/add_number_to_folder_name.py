import json
import os
import re


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LESSONS_PATH = os.path.join(PROJECT_ROOT, "youtube_data", "Johnny Harris", "lessons")

list_number_lessons = []
lesson_paths = []

# modify these foldername, because the lesson_number can be 1a, 2b, 3c

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
        #  lesson_number can be 1a, 2b, 3c, take the number and the text
        match = re.fullmatch(r"(\d+)([A-Za-z]*)", str(lesson_number).strip())
        if not match:
            raise ValueError(f"{folder_name}: lesson_number is missing or invalid")
        number_part, text_part = match.groups()

        # check if the folder name already starts with a number
        if re.match(r"^\d{3}[A-Za-z]* - ", folder_name):
            print(f"{folder_name}: folder already has a number prefix, skipping")
            continue

    new_folder_name = f"{int(number_part):03d}{text_part} - {folder_name}"

    new_lesson_path = os.path.join(LESSONS_PATH, new_folder_name)
    os.rename(lesson_path, new_lesson_path)
    print(f"Renamed folder: {folder_name} -> {new_folder_name}")