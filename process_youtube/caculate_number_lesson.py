import json
import os


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LESSONS_PATH = os.path.join(PROJECT_ROOT, "youtube_data", "English Stories", "lessons")

list_number_lessons = []
lesson_paths = []

for folder_name in sorted(os.listdir(LESSONS_PATH)):
    lesson_path = os.path.join(LESSONS_PATH, folder_name)
    if not os.path.isdir(lesson_path):
        continue

    lesson_paths.append(lesson_path)
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

        list_number_lessons.append(lesson_number)

sorted_list_number_lessons = sorted(list_number_lessons)

dict_convert = {number: index + 1 for index, number in enumerate(sorted_list_number_lessons)}


# Convert to new lesson_number.
for lesson_path in lesson_paths:
    folder_name = os.path.basename(lesson_path)
    description_path = os.path.join(lesson_path, "description.json")
 
    with open(description_path, "r", encoding="utf-8") as f:
        description = json.load(f)
        if not isinstance(description, dict):
            raise ValueError(f"{folder_name}: description.json is not a JSON object")
        lesson_number = description.get("lesson_number")

    
        new_lesson_number = dict_convert[lesson_number]
        description["lesson_number"] = new_lesson_number

    with open(description_path, "w", encoding="utf-8") as f:
        json.dump(description, f, ensure_ascii=False, indent=4)

    print(f"{folder_name}: updated lesson_number to {new_lesson_number}")


