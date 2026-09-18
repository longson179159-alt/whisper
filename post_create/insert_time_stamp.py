
import os
import json
import shutil
NEW_TIMESATMP_SOURSE = r"C:\Users\PC\Desktop\raw_whisper\greate_gastby"
DESTINATION = r"C:\Users\PC\Desktop\kaggle\whisper\en\gatsby_the_greate\lessons"
# raw_timestamp.json
for folder_name in os.listdir(DESTINATION):
    folder_path = os.path.join(DESTINATION, folder_name)
    if not os.path.isdir(folder_path):
        continue

    raw_timestamp_path = os.path.join(NEW_TIMESATMP_SOURSE, folder_name, 'raw_timestamp.json')
    if not os.path.isfile(raw_timestamp_path):
        print(f'Missing the raw timestamp file with {folder_name}')
        continue

    new_destination_path = os.path.join(DESTINATION, folder_name, 'raw_timestamp.json')

    shutil.copy2(raw_timestamp_path, new_destination_path)

print('finished process!')