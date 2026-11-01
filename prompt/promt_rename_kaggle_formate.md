Work on this course:

COURSE_ROOT = "<ABSOLUTE_PATH_TO_COURSE>"
COURSE_NAME = "<HUMAN_READABLE_COURSE_NAME>"
AUDIO_FOLDER_NAME = "<NAME_OF_FLAT_AUDIO_FOLDER>"

The expected input structure is:

<COURSE_ROOT>/
├── course_infos/
├── <AUDIO_FOLDER_NAME>/
│   ├── 1.First Lesson.mp3
│   ├── 2. Second Lesson.mp3
│   └── ...
└── lessons/
    ├── 1.First Lesson/
    │   ├── 1.First Lesson.mp3
    │   └── 1.First Lesson.txt
    ├── 2. Second Lesson/
    │   ├── 2. Second Lesson.mp3
    │   └── 2. Second Lesson.txt
    └── ...

The flat audio folder contains the original MP3 files.

Each folder under `lessons` represents one lesson. Before renaming, its folder name and MP3 filename normally share the same stem. A lesson may also contain a text file and other files.

Inspect the real directory first. Do not assume that every optional file exists.

Complete these tasks:

1. Create the course description

Create:

<COURSE_ROOT>/course_infos/description.json

Content:

{
  "course_number": null,
  "course_name": "<COURSE_NAME>",
  "author": null,
  "content_language": null,
  "type": null,
  "audio_duration": null,
  "is_system_course": null,
  "avatar": null,
  "has_lesson_images": null,
  "level": null,
  "youtube_id": null,
  "url": null
}

Only `course_name` may contain a value. Every other field must be JSON `null`.

2. Create lesson descriptions

Inside every immediate subfolder of:

<COURSE_ROOT>/lessons

create:

description.json

Use this structure:

{
  "lesson_number": null,
  "lesson_name": "<HUMAN_READABLE_LESSON_NAME>",
  "level": null,
  "youtube_id": null,
  "url": null,
  "audio_start_time": null,
  "audio_duration": null,
  "has_sentence_timestamps": null
}

Only `lesson_name` may contain a value. Every other field must be JSON `null`.

Derive the human-readable lesson name from the original folder name by removing only its leading lesson number, optional period, and following spaces.

Examples:

- `1.Hello` becomes `Hello`
- `2. How Are You` becomes `How Are You`
- `10. Did You Go Out Yesterday` becomes `Did You Go Out Yesterday`

Keep spaces, punctuation, and apostrophes in the JSON `lesson_name`.

3. Apply safe filesystem names

Rename lesson folders and MP3 files using this exact Python rule:

re.sub(r"[^a-zA-Z0-9._-]", "_", name)

Examples:

- `1.The New Neighbor` becomes `1.The_New_Neighbor`
- `6. Do You Have a Pet` becomes `6._Do_You_Have_a_Pet`
- `13. I'll Help You` becomes `13._I_ll_Help_You`
- `8. Goodbye! See You Later` becomes `8._Goodbye__See_You_Later`

Apply this rule to:

- Every `.mp3` directly inside `<AUDIO_FOLDER_NAME>`
- Every `.mp3` inside each lesson folder
- Every immediate lesson folder under `lessons`

Do not rename:

- `.txt` files
- `description.json`
- Other lesson assets
- The human-readable `lesson_name` inside JSON

4. Add a reusable renaming script

Create:

<COURSE_ROOT>/change_name.py

The script must:

- Use `Path(__file__).resolve().parent` as the course root
- Define the flat audio directory from `AUDIO_FOLDER_NAME`
- Use the exact safe-name regex
- Rename flat MP3 files
- Rename MP3 files inside lesson folders
- Rename lesson folders
- Check whether the destination already exists
- Raise `FileExistsError` rather than overwrite anything
- Skip names that are already safe
- Be safe to run repeatedly

5. Preserve future naming

Inspect any TTS generation scripts inside the course root.

Update their MP3 output naming so newly generated MP3 files use the same regex. Do not change voice settings, dialogue parsing, pauses, input locations, or other behavior.

Do not run Google TTS or make any API request.

6. Execute and verify

Run `change_name.py` once.

Then verify:

- Exactly one course description exists
- Every lesson folder contains a description
- All description files contain valid JSON
- Only `course_name` is non-null in the course description
- Only `lesson_name` is non-null in lesson descriptions
- Every lesson folder has a safe filesystem name
- Every MP3 has a safe filename
- The MP3 inside each lesson matches the sanitized lesson-folder stem
- Text files and other assets were not renamed
- No files were overwritten
- `git -c core.whitespace=cr-at-eol diff --check` passes if this is a Git repository

Finish by reporting:

- Course name
- Number of lesson descriptions created
- Number of lesson folders renamed
- Number of MP3 files renamed
- Any missing or unexpected input files