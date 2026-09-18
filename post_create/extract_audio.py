import os
from shutil import copy

OUTPUT_FOLDER = r"C:\Users\PC\Desktop\kaggle\whisper\audio"
WORKING_FOLDER = r"C:\Users\PC\Desktop\kaggle\whisper\en"

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

for course_name in os.listdir(WORKING_FOLDER):
    course_path = os.path.join(WORKING_FOLDER, course_name)
    if not os.path.isdir(course_path):
        continue

    lessons_folder_path = os.path.join(course_path, "lessons")
    if not os.path.isdir(lessons_folder_path):
        continue

    output_folder_path = os.path.join(OUTPUT_FOLDER, course_name)
    os.makedirs(output_folder_path, exist_ok=True)

    for lesson_name in os.listdir(lessons_folder_path):
        lesson_path = os.path.join(lessons_folder_path, lesson_name)
        if not os.path.isdir(lesson_path):
            continue

        audio_path = os.path.join(lesson_path, "audio.mp3")
        if not os.path.isfile(audio_path):
            raise FileNotFoundError(f"Missing audio file: {audio_path}")

        output_audio_path = os.path.join(output_folder_path, f"{lesson_name}.mp3")
        copy(audio_path, output_audio_path)