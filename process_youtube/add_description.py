
import argparse
from ast import arg
import os

import json
# from urllib.parse import parse_qs, urlparse
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


CURRENT_FOLDER = 'short story for learning english/lessons'
CURRENT_FOLDER_PATH = os.path.join(PROJECT_ROOT, 'youtube_data', CURRENT_FOLDER)  # Path to the folder containing the text and raw timestamp files.

def get_url(youtube_id: str) -> str:
    """Return the watch URL for an 11-character YouTube video ID."""
    if not isinstance(youtube_id, str) or len(youtube_id) != 11:
        raise ValueError("youtube_id must be an 11-character string")

    return f"https://www.youtube.com/watch?v={youtube_id}"
def main():
    # add level agument
    parser = argparse.ArgumentParser(description="Add description.json to each lesson folder.")
    parser.add_argument(
        "--level",
        type=str,
        default="b1",
        help="Level of the lesson (default: b1)",
    )
    # # is_youtube_video argument
    # parser.add_argument(
    #     "--is_youtube_video",
    #     action="store_true",
    #     help="Indicates if the lesson is a YouTube video",
    # )

    arg = parser.parse_args()


    for idx, folder_name in enumerate(sorted(os.listdir(CURRENT_FOLDER_PATH))):
        folder_path = os.path.join(CURRENT_FOLDER_PATH, folder_name)
        if not os.path.isdir(folder_path):
            continue

        has_sentence_timestamps = False

        # caculate the audio duration
        audio_files = [f for f in os.listdir(folder_path) if f.lower().endswith(".mp3")]
        audio_path = os.path.join(folder_path, audio_files[0])
        # caculate the actual duration of the audio file using pydub
        from pydub import AudioSegment
        audio_duration = AudioSegment.from_mp3(audio_path).duration_seconds

        # read old description.json if exists
        # description_path = os.path.join(folder_path, "description.json")
        old_description = {}
        if os.path.exists(os.path.join(folder_path, "description.json")):
            with open(os.path.join(folder_path, "description.json"), "r", encoding="utf-8") as file:
                old_description = json.load(file)

        # youtube_id = None
        # if arg.is_youtube_video:
        #     url = old_description.get("url", "")
        #     # extract youtube_id from url
        #     youtube_id = parse_qs(urlparse(url).query).get("v", [None])[0]

        description = {
            # round the audio duration to 2 decimal places
            "lesson_number": old_description.get("lesson_number") or idx + 1,
            "lesson_name": old_description.get("lesson_name") or folder_name,
            "level": old_description.get("level") or arg.level,
            "youtube_id": old_description.get("youtube_id") ,
            "url": old_description.get("url", "") or get_url(old_description.get("youtube_id")),
            "audio_start_time": old_description.get("audio_start_time", 0),
            "audio_duration": old_description.get("audio_duration", round(audio_duration, 2)),
            "has_sentence_timestamps": old_description.get("has_sentence_timestamps", has_sentence_timestamps),
        }
        description_path = os.path.join(folder_path, "description.json")

        with open(description_path, "w", encoding="utf-8") as file:
            json.dump(description, file, ensure_ascii=False, indent=4)

        print(f"Created description.json in {folder_path}")

if __name__ == "__main__":
    main()


# python process_youtube/add_description.py --level b1