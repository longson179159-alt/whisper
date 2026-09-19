

import os

# remove lesson.json and timestamp.json, raw_timestamp.json
WORKING_FOLDER = r"C:\Users\PC\Desktop\kaggle\whisper\en\how_to_stop_worrying_and_start_living\lessons"
# C:\Users\PC\Desktop\kaggle\whisper\en\gatsby_the_greate
# C:\Users\PC\Desktop\kaggle\whisper\en\how_to_stop_worrying_and_start_living
for folder_name in os.listdir(WORKING_FOLDER):  
    
    folder_path = os.path.join(WORKING_FOLDER, folder_name)
    if not os.path.isdir(folder_path):
        continue

    lesson_json_path = os.path.join(folder_path, "lesson.json")
    if os.path.isfile(lesson_json_path):
        os.remove(lesson_json_path)
        print(f"Removed {lesson_json_path}")
    if os.path.isfile(os.path.join(folder_path, "timestamp.json")):
        os.remove(os.path.join(folder_path, "timestamp.json"))
        print(f"Removed {os.path.join(folder_path, 'timestamp.json')}")

    if os.path.isfile(os.path.join(folder_path, "raw_timestamp.json")):
        os.remove(os.path.join(folder_path, "raw_timestamp.json"))
        print(f"Removed {os.path.join(folder_path, 'raw_timestamp.json')}")

    

   