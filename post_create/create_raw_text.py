import os
import json

WORKING_FOLDER = r"C:\Users\PC\Desktop\kaggle\whisper\en\English Stories\lessons"

# read the text in timestamp and save it in raw_text.txt,
# create a text.txt with empty conttent
# change the name of timmstamp.json to youtube_timestamp.json

for folder_name in os.listdir(WORKING_FOLDER):
    
    folder_path = os.path.join(WORKING_FOLDER, folder_name)
    if not os.path.isdir(folder_path):
        continue

    timestamp_json_path = os.path.join(folder_path, "timestamp.json")
    if not os.path.isfile(timestamp_json_path):
        print(f"Missing timestamp.json in {folder_path}")
        continue

    with open(timestamp_json_path, "r", encoding="utf-8") as f:
        timestamp_data = json.load(f)

    raw_text = "\n".join(item["text"] for item in timestamp_data)
    raw_text_path = os.path.join(folder_path, "raw_text.txt")
    with open(raw_text_path, "w", encoding="utf-8") as f:
        f.write(raw_text)

    text_txt_path = os.path.join(folder_path, "text.txt")
    with open(text_txt_path, "w", encoding="utf-8") as f:
        f.write("")

    youtube_timestamp_json_path = os.path.join(folder_path, "youtube_timestamp.json")
    os.rename(timestamp_json_path, youtube_timestamp_json_path)