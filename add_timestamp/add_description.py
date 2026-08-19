
import os

import json
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


CURRENT_FOLDER = '6_minute_bbc/lessons'
CURRENT_FOLDER_PATH = os.path.join(PROJECT_ROOT, 'en', CURRENT_FOLDER)  # Path to the folder containing the text and raw timestamp files.


def main():
    # add_descriptions = []

    for folder_name in sorted(os.listdir(CURRENT_FOLDER_PATH)):
        folder_path = os.path.join(CURRENT_FOLDER_PATH, folder_name)
        if not os.path.isdir(folder_path):
            continue

        has_sentence_timestamps = True

        # caculate the audio duration
        audio_files = [f for f in os.listdir(folder_path) if f.lower().endswith(".mp3")]
        audio_path = os.path.join(folder_path, audio_files[0])
        # caculate the actual duration of the audio file using pydub
        from pydub import AudioSegment
        audio_duration = AudioSegment.from_mp3(audio_path).duration_seconds

        description = {
            # round the audio duration to 2 decimal places
            "url" : "",
            "audio_start_time": 0,
            "audio_duration": round(audio_duration, 2),
            "has_sentence_timestamps": has_sentence_timestamps
        }
        description_path = os.path.join(folder_path, "description.json")

        with open(description_path, "w", encoding="utf-8") as file:
            json.dump(description, file, ensure_ascii=False, indent=4)

        print(f"Created description.json in {folder_path}")

if __name__ == "__main__":
    main()