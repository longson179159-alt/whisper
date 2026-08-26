# Schema for Creating Langoda Lesson Folders

This document describes the expected folder structure and workflows for creating Langoda courses and lessons from audio or YouTube videos.

## Example Output

### Lesson Folder Tree

```text
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
```

### Course Description

```json
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
  "url": "https://www.youtube.com/watch?v=kUM7FBP6Lj4&list=PLAg1DP01xg5uh1XNnHo57BWXjKAbsFk5M"
}
```

### Lesson Description

```json
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
```

## Workflows

### 1. Audio and Text Are Available

Use this workflow for sources such as Listen A Minute and BBC 6 Minute English.

1. Run `en.ipynb` or `zh.ipynb` in Kaggle to generate the initial transcription files.

   ```text
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
   ```

2. Measure Whisper transcription accuracy.

   ```powershell
   python metrics\CheckWhisperRawText.py
   ```

3. Create lesson images using the prompt in `prompt_lesson_picture.txt`.

4. Add the descriptions, `lesson.json`, and `timestamp.json` files.

   ```powershell
   python add_timestamp\add_description.py --level a1 --is_youtube_video
   python add_timestamp\add_lesson.py
   python add_timestamp\timestamp.py
   ```

5. Create the course description and calculate total course audio duration.

   ```powershell
   python add_timestamp/add_audio_durations.py
   ```

6. Manually refine the course description.

### 2. YouTube Videos (Zoe's Languages)

1. Export `timestamp.json` and `lesson.json` with the browser extension.

   ![YouTube creation workflow](youtube%20create.png)

2. Download the thumbnail and audio, then add the descriptions.

   ```powershell
   python process_youtube\download_thumbnail.py
   python process_youtube\download_audio.py
   python process_youtube\add_description.py --level b1
   ```

3. Review and refine the generated course description.

```
   python add_timestamp/add_audio_durations.py
```

### 3. Audio Is Available but Text Is Missing

Use this workflow for a long audio source such as `I_can_do_it`.

1. Run `en.ipynb` or `zh.ipynb` in Kaggle to generate the initial transcription files.

   ```text
   I_can_do_it
   |-- audio.mp3
   |-- raw_text.txt
   |-- raw_timestamp.json
   `-- text.txt
   ```

2. Add lesson timestamps (list_lessons.json) to split the long course audio into individual lessons.

   Each item in the timestamp JSON contains:

   - `lessonFolderName`: The destination folder/name for the lesson.
   - `startTime`: The time in the source audio at which the lesson starts.

   ```json
   [
     {
       "lessonFolderName": "Introduction to Affirmations",
       "startTime": "0:00"
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

3. Create lesson subfolders for large audio files.

   ```powershell
   python process_youtube\createSmallLessons.py
   ```

   This creates the lesson audio, descriptions, `timestamp.json`, and `text.txt` files.

4. Add `lesson.json` to every sublesson.

   ```powershell
   python add_timestamp\add_lesson.py
   ```

5. Create and refine the course description.

   ```powershell
   python add_timestamp/add_audio_durations.py
   ```
