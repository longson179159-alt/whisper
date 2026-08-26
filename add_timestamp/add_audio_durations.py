import os
import json
from pydub import AudioSegment


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIRST_FOLDER = 'en'
SECOND_FOLDER = 'youtube_data'
FIRST_FOLDER_PATH = os.path.join(PROJECT_ROOT, FIRST_FOLDER)
SECOND_FOLDER_PATH = os.path.join(PROJECT_ROOT, SECOND_FOLDER)


def calculate_course_audio_duration(folder_course_path):
    total_duration = 0

    folder_containing_lessons = os.path.join(folder_course_path, 'lessons')

    if not os.path.exists(folder_containing_lessons):
        raise FileNotFoundError(f"Missing lessons folder in {folder_course_path}")
    for lesson_folder in os.listdir(folder_containing_lessons):
        lesson_path = os.path.join(folder_containing_lessons, lesson_folder)
        if os.path.isdir(lesson_path):
            lesson_audio_path = os.path.join(lesson_path, 'audio.mp3')
            if os.path.exists(lesson_audio_path):
                
                audio_duration = AudioSegment.from_mp3(lesson_audio_path).duration_seconds
                total_duration += audio_duration
            else:
                raise FileNotFoundError(f"Missing audio.mp3 in {lesson_path}")
    return round(total_duration, 2)  # Return the total duration rounded to 2 decimal places



def add_course_infos(folder_course_path):
    description_path = os.path.join(folder_course_path, 'course_infos', 'description.json')

    audio_course_duration = calculate_course_audio_duration(folder_course_path)
    if not os.path.exists(description_path):
        course_description = {
            "course_number": None,
            "course_name": None,
            "author": None,
            "content_language": None,
            "type": "['beginner', 'daily life']",
            "audio_duration": audio_course_duration,
            "is_system_course": True,
            "avatar": None,
            "has_lesson_images": True,
            "level": None,
            "youtube_id": None,
            "url": None
            }
        os.makedirs(os.path.dirname(description_path), exist_ok=True)
        with open(description_path, 'w', encoding='utf-8') as file:
            json.dump(course_description, file, ensure_ascii=False, indent=2)
    else:
        with open(description_path, "r", encoding="utf-8") as file:
            course_description = json.load(file)

        course_description["audio_duration"] = audio_course_duration

        with open(description_path, "w", encoding="utf-8") as file:
            json.dump(course_description, file, ensure_ascii=False, indent=2)

    # print audio duration for verification
    print(f"Audio duration for course '{os.path.basename(folder_course_path)}': {audio_course_duration} seconds")



def main():
    for course_root  in (FIRST_FOLDER_PATH, SECOND_FOLDER_PATH):
        for folder_course_name in sorted(os.listdir(course_root)):
            folder_course_path = os.path.join(course_root, folder_course_name)
            if not os.path.isdir(folder_course_path):
                continue

            add_course_infos(folder_course_path)

            print(f"Finished processing {folder_course_name}")
 



if __name__ == "__main__":
    main()

# python add_timestamp/add_audio_durations.py