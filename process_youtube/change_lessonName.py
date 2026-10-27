working_folder_path = r"D:\english course\System_course\c1\The_alchemist\lessons"

import os
import json

# change chuck_1, chuck_2... to Part 1, Part 2...

for folder_name in sorted(os.listdir(working_folder_path)):
    description_path = os.path.join(working_folder_path, folder_name, "description.json")
    with open(description_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    lesson_name = data.get("lesson_name")
    print(f"{folder_name}: {lesson_name}")
    data["lesson_name"] = lesson_name.replace("chuck_", "Part ")
    with open(description_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    rename_folder_name = folder_name.replace("chuck_", "Part ")
    rename_folder_path = os.path.join(working_folder_path, rename_folder_name)
    os.rename(os.path.join(working_folder_path, folder_name), rename_folder_path)

