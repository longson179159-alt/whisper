import os
import json
import argparse
from ast import arg
import yt_dlp
from pydub import AudioSegment

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)


# C:\Users\PC\Desktop\whisper\youtube_data\
CURRENT_FOLDER = "I_can_do_id"
CURRENT_FOLDER_PATH = os.path.join(PROJECT_ROOT, 'youtube_data', CURRENT_FOLDER)


description_path = os.path.join(CURRENT_FOLDER_PATH, 'description.json')
with open(description_path, 'r', encoding='utf') as file1:
    description = json.load(file1)

timestamp_path = os.path.join(CURRENT_FOLDER_PATH, 'timestamp.json') 
with open(timestamp_path, 'r', encoding='utf-8') as file2:
    globalTimestamp = json.load(file2)


list_lessons_path = os.path.join(CURRENT_FOLDER_PATH, 'list_lessons.json')
with open(list_lessons_path, 'r', encoding='utf-8') as file3:
    listLessons = json.load(file3)

def download_audio(CURRENT_FOLDER_PATH, youtube_id: str) -> None:
    """Download one YouTube video's audio as ``audio.mp3``."""
    options = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(CURRENT_FOLDER_PATH, "audio.%(ext)s"),
        "noplaylist": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    }
    url = f"https://www.youtube.com/watch?v={youtube_id}"
    with yt_dlp.YoutubeDL(options) as downloader:
        downloader.download([url])

# download thumbnail
def download_thumbnail(CURRENT_FOLDER_PATH, youtube_id: str) -> None:
    """Download one YouTube video's thumbnail as ``thumbnail.jpg``."""
    options = {
            "outtmpl": os.path.join(CURRENT_FOLDER_PATH, "thumbnail.%(ext)s"),
            "noplaylist": True,
            "skip_download": True,
            "writethumbnail": True,
            "postprocessors": [
                {
                    "key": "FFmpegThumbnailsConvertor",
                    "format": "jpg",
                }
            ],
        }
    url = f"https://www.youtube.com/watch?v={youtube_id}"
    with yt_dlp.YoutubeDL(options) as downloader:
        downloader.download([url])

def to_seconds(value: str) -> int:
    parts = [int(part) for part in value.split(":")]

    if len(parts) == 2:  # MM:SS
        minutes, seconds = parts
        return minutes * 60 + seconds

    if len(parts) == 3:  # HH:MM:SS
        hours, minutes, seconds = parts
        return hours * 3600 + minutes * 60 + seconds

    raise ValueError(f"Invalid time format: {value}")

# add endtime
listLessonsAddEnd = []
for idx, lesson in enumerate(listLessons):
    end = (
    to_seconds(listLessons[idx + 1]["startTime"])
    if idx < len(listLessons) - 1
    else globalTimestamp[-1]["end"]
)

    listLessonsAddEnd.append({
        'start':to_seconds(lesson["startTime"]),
        'end': end,
        "lessonFolderName": lesson['lessonFolderName']
    })

def main():

    if not os.path.exists(os.path.join(CURRENT_FOLDER_PATH, 'audio.mp3')):
        download_audio(CURRENT_FOLDER_PATH, description['youtube_id'])
    else:
        print(f"audio.mp3 already exists in {CURRENT_FOLDER_PATH}, skipping download.")

    if not os.path.exists(os.path.join(CURRENT_FOLDER_PATH, 'thumbnail.jpg')):
        download_thumbnail(CURRENT_FOLDER_PATH, description['youtube_id'])
    else:
        print(f"thumbnail.jpg already exists in {CURRENT_FOLDER_PATH}, skipping download.")

    parser = argparse.ArgumentParser(description="Add description.json to each lesson folder.")
    parser.add_argument(
        "--level",
        type=str,
        default="b1",
        help="Level of the lesson (default: b1)",
    )

    arg = parser.parse_args()

    for idx, lesson in enumerate(listLessonsAddEnd):



        currentStart = lesson['start']
        currentEnd = lesson['end']
        lessonFolderName = lesson["lessonFolderName"]
        lessonFolderPath = os.path.join(CURRENT_FOLDER_PATH, 'lessons', lessonFolderName)
        os.makedirs(lessonFolderPath, exist_ok = True)

        subTimestamp = [
            {
                **ts,
                "start": ts["start"] - currentStart,
                "end": ts["end"] - currentStart
            }
            for ts in globalTimestamp
            if ts["start"] >= currentStart and ts["end"] <= currentEnd
        ]
                

        subTimestampPath = os.path.join(lessonFolderPath, 'timestamp.json')
        with open(subTimestampPath, 'w', encoding='utf-8') as file:
            json.dump(subTimestamp, file, ensure_ascii=False, indent=4)

        subText = '\n'.join(ts['text'] for ts in subTimestamp)
        textFilePath = os.path.join(lessonFolderPath, 'text.txt')
        with open(textFilePath, 'w', encoding='utf-8') as file:
            file.write(subText)

        subLessonDescription = {
            "lesson_number": idx +1,
            'lesson_name': lessonFolderName,
            "level": arg.level,
            "youtube_id": None,
            "url": description['youtube_url'],

            "audio_start_time": 0,
            "audio_duration": currentEnd - currentStart, 
            "has_sentence_timestamps": False

        }

        subLessonDescriptionPath = os.path.join(lessonFolderPath, 'description.json')
        with open(subLessonDescriptionPath, 'w', encoding='utf-8') as file:
            json.dump(subLessonDescription, file, ensure_ascii=False, indent=4)

        # take a slice of the audio.mp3 file from currentStart to currentEnd and save it as audio.mp3 in the lesson folder
        # save audio as mp3 using pydub
        audio = AudioSegment.from_mp3(os.path.join(CURRENT_FOLDER_PATH, 'audio.mp3'))
        audio = audio[currentStart * 1000:currentEnd * 1000]  # Convert to milliseconds
        audio.export(os.path.join(lessonFolderPath, 'audio.mp3'), format='mp3')
        


if __name__ == "__main__":
    main()
# {
#     "lesson_number": 10,
#     "lesson_name": "5 Habits That Made Me A Successful Language Learner",
#     "level": "b1",
#     "youtube_id": "tnSPMi0pYNc",
#     "url": "https://www.youtube.com/watch?v=tnSPMi0pYNc",


#     "audio_start_time": 0,
#     "audio_duration": 553.6,
#     "has_sentence_timestamps": false
# }


    
