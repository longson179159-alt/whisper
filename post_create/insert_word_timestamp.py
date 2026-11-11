from pathlib import Path
import shutil
import sys


# ============================================================
# CONFIG
# ============================================================

TARGET_COURSE = Path(
    input("Enter target course folder path: ").strip().strip('"').strip("'")
)

WHISPER_OUTPUT = Path(
    input("Enter Whisper output folder path: ").strip().strip('"').strip("'")
)

# ============================================================
# VALIDATION
# ============================================================

def main():
    print("Checking folders...")

    if not TARGET_COURSE.is_dir():
        raise FileNotFoundError(
            f"Target course does not exist:\n{TARGET_COURSE}"
        )

    if not WHISPER_OUTPUT.is_dir():
        raise FileNotFoundError(
            f"Whisper output does not exist:\n{WHISPER_OUTPUT}"
        )

    lessons_dir = TARGET_COURSE / "lessons"

    if not lessons_dir.is_dir():
        raise FileNotFoundError(
            f"Target lessons folder does not exist:\n{lessons_dir}"
        )

    # --------------------------------------------------------
    # 1. Check Whisper folder name
    #
    # Target:
    #   English A1
    #
    # Expected Whisper output:
    #   English A1_audios
    # --------------------------------------------------------

    expected_whisper_name = f"{TARGET_COURSE.name}_audios"

    if WHISPER_OUTPUT.name != expected_whisper_name:
        raise ValueError(
            "\nWhisper output folder name does not match target course.\n"
            f"Target course:           {TARGET_COURSE.name}\n"
            f"Expected Whisper folder: {expected_whisper_name}\n"
            f"Actual Whisper folder:   {WHISPER_OUTPUT.name}"
        )

    print(f"✓ Folder name matches: {expected_whisper_name}")

    # --------------------------------------------------------
    # 2. Get lesson folder names
    # --------------------------------------------------------

    target_lessons = {
        folder.name
        for folder in lessons_dir.iterdir()
        if folder.is_dir()
    }

    whisper_lessons = {
        folder.name
        for folder in WHISPER_OUTPUT.iterdir()
        if folder.is_dir()
    }

    print(f"Target lessons:  {len(target_lessons)}")
    print(f"Whisper lessons: {len(whisper_lessons)}")

    # --------------------------------------------------------
    # 3. Compare lesson folders
    # --------------------------------------------------------

    missing_in_whisper = target_lessons - whisper_lessons
    extra_in_whisper = whisper_lessons - target_lessons

    if missing_in_whisper or extra_in_whisper:

        print("\nERROR: Lesson folders do not match.")

        if missing_in_whisper:
            print("\nMissing in Whisper output:")
            for name in sorted(missing_in_whisper):
                print(f"  - {name}")

        if extra_in_whisper:
            print("\nExtra in Whisper output:")
            for name in sorted(extra_in_whisper):
                print(f"  - {name}")

        sys.exit(1)

    print("✓ All lesson folder names match.")

    # --------------------------------------------------------
    # 4. Check every word_timestamp.json exists
    # BEFORE copying anything
    # --------------------------------------------------------

    missing_timestamp_files = []

    for lesson_name in sorted(target_lessons):
        source = WHISPER_OUTPUT / lesson_name / "word_timestamp.json"

        if not source.is_file():
            missing_timestamp_files.append(source)

    if missing_timestamp_files:
        print("\nERROR: Missing word_timestamp.json files:")

        for path in missing_timestamp_files:
            print(f"  - {path}")

        print("\nNothing was copied.")
        sys.exit(1)

    print("✓ Every Whisper lesson has word_timestamp.json.")

    # --------------------------------------------------------
    # 5. Copy files
    # --------------------------------------------------------

    print("\nCopying word_timestamp.json files...\n")

    copied = 0

    for lesson_name in sorted(target_lessons):

        source = (
            WHISPER_OUTPUT
            / lesson_name
            / "word_timestamp.json"
        )

        destination = (
            lessons_dir
            / lesson_name
            / "word_timestamp.json"
        )

        shutil.copy2(source, destination)

        print(f"✓ {lesson_name}")
        copied += 1

    # --------------------------------------------------------
    # DONE
    # --------------------------------------------------------

    print("\n========================================")
    print("SUCCESS")
    print("========================================")
    print(f"Copied: {copied} word_timestamp.json files")
    print(f"Target: {lessons_dir}")


if __name__ == "__main__":
    main()