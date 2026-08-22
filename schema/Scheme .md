Schema for creating Langoda lesson folders

# Example of output

## Lesson folder tree

zoe_languages
|-- course_infos
|   |-- avatar.jpg
|   |-- description.json
|   `-- image.jpg
|
`-- lessons
    |-- 5 Habits That Made Me A Successful Language Learner
    |   |-- audio.mp3
    |   |-- description.json
    |   |-- image.jpg
    |   |-- lesson.json
    |   `-- timestamp.json
    |
    |-- Eastern VS Western Learning Styles Which Are More Effective
    |   |-- audio.mp3
    |   |-- description.json
    |   |-- image.jpg
    |   |-- lesson.json
    |   `-- timestamp.json
    |
    `-- ...

## Course description
{
  "course_number": 1,
  "course_name": "Productivity and Language Learning",
  "author": "Zoes Languages",
  "content_language": "en",
  "type": "['productivity', 'language learning', 'study vlog']",
  "audio_duration": 6898.38,
  "is_system_course": false,
  "avatar": "avatar.jpg",
  "has_lesson_images": true,
  "level": "b1",
  "youtube_id": "PLAg1DP01xg5uh1XNnHo57BWXjKAbsFk5M",
  "youtube_url": "https://www.youtube.com/watch?v=kUM7FBP6Lj4&list=PLAg1DP01xg5uh1XNnHo57BWXjKAbsFk5M"
}

## Lesson description
{
    "lesson_number": 4,
    "lesson_name": "【Study Vlog】How do I study languages on a busy day (subtitles)",
    "level": "b1",
    "youtube_id": "y4VrWc0PM3M",
    "url": "https://www.youtube.com/watch?v=y4VrWc0PM3M",
    "audio_start_time": 0,
    "audio_duration": 920.27,
    "has_sentence_timestamps": false
}

# Schema

## 1. With audios and texts available (listen a minute, bbc 6 minutes)
### run en.ipynb or zh.ipynb in kaggle to get 
example:

    闹闹故事
|-- story_one
|   |-- audio.mp3
|   |-- raw_text.txt
|   |-- raw_timestamp.json
|   `-- text.txt
|
|-- story_two
|   |-- audio.mp3
|   |-- raw_text.txt
|   |-- raw_timestamp.json
|   `-- text.txt
|
`-- ...

### measures Whisper transcription accuracy.
python metrics\CheckWhisperRawText.py

## Create images with Chat gpt
prompt_lesson_picture.txt

### Add description, lesson.json, timestamp.json
#### description
example command
python add_timestamp/add_description.py --level a1 --is_youtube_video

#### Add lesson.json

python add_timestamp/add_lesson.py 

#### Add timestamp.json

python add_timestamp/timestamp.py 

#### Add course description and calculate the course audio duration

python process_youtube/add_description.py --level b1

then manually refine course desciption

## YouTube video (Zoe's Language)

### Get timestamp.json and lesson.json from the extension


![YouTube create](youtube%20create.png)

### download thumbnail, audio, then add description

python process_youtube/download_thumbnail.py
python process_youtube/download_audio.py
python process_youtube/add_description.py --level b1

#### Add course description and calculate the course audio duration

python process_youtube/add_description.py --level b1


## Have audios, but miss the text (I_can_do_it)
run en.ipynb or zh.ipynb in kaggle to get 

|-- I_can_do_it
|   |-- audio.mp3
|   |-- raw_text.txt
|   |-- raw_timestamp.json
|   `-- text.txt

### Add Lesson Timestamps

This JSON defines how a long audio course is divided into individual lessons.

Each item contains:

- `lessonFolderName`: the folder/name of the lesson.
- `startTime`: the time in the original audio where the lesson begins.

### Example

```json
[
  {
    "lessonFolderName": "Introduction to Affirmations",
    "startTime": "0:0"
  },
  {
    "lessonFolderName": "Health",
    "startTime": "18:05"
  },
  {
    "lessonFolderName": "Forgiveness",
    "startTime": "24:15"
  }
]
```

###  Create sub lessons (apply for large audios)
python process_youtube\createSmallLessons.py

this create audios, descriptions, timestamp.json, and text.txt

### Add lesson.json for each sublesson
python add_timestamp/add_lesson.py 

#### Add course description and calculate the course audio duration

python process_youtube/add_description.py --level b1

then manually refine course description




