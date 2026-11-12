"""Validate local Langoda course trees before S3 upload and Django import.

Examples:
    python check_ready_course.py
    python check_ready_course.py --language en
    python check_ready_course.py --language zh
    python check_ready_course.py --project-root C:\path\to\whisper

The default run checks both ``en`` and ``zh`` below the Whisper project root.
The script never changes course files. It exits with status 0 only when every
selected branch and every discovered course passes all checks.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


LANGUAGES = ("en", "zh")
LEVELS = {"a1", "a2", "b1", "b2", "c1", "c2"}
COURSE_REQUIRED_FIELDS = {
    "course_number",
    "course_name",
    "content_language",
    "type",
    "audio_duration",
    "level",
}
LESSON_REQUIRED_FIELDS = {
    "lesson_number",
    "lesson_name",
    "level",
    "audio_start_time",
    "audio_duration",
    "has_sentence_timestamps",
}
BASE_LESSON_FILES = (
    "audio.mp3",
    "description.json",
    "lesson.json",
    "timestamp.json",
)


@dataclass
class CourseResult:
    language: str
    relative_path: Path
    lesson_count: int = 0
    measured_duration: float = 0.0
    errors: list[str] = field(default_factory=list)

    @property
    def ready(self) -> bool:
        return not self.errors


@dataclass
class BranchResult:
    language: str
    root: Path
    courses: list[CourseResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def ready(self) -> bool:
        return not self.errors and bool(self.courses) and all(
            course.ready for course in self.courses
        )


def parse_arguments() -> argparse.Namespace:
    default_project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description=(
            "Check en/zh course folders before all_courses.py upload and "
            "import_all_system_course.py import."
        )
    )
    parser.add_argument(
        "--language",
        choices=("all", *LANGUAGES),
        default="all",
        help="Branch to check. Default: both en and zh.",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=default_project_root,
        help=(
            "Whisper project directory containing en/ and zh/. "
            f"Default: {default_project_root}"
        ),
    )
    parser.add_argument(
        "--ffprobe",
        type=Path,
        help="Optional explicit path to ffprobe.exe.",
    )
    return parser.parse_args()


def find_ffprobe(explicit_path: Path | None) -> Path | None:
    candidates: list[Path] = []
    if explicit_path is not None:
        candidates.append(explicit_path.expanduser())

    on_path = shutil.which("ffprobe")
    if on_path:
        candidates.append(Path(on_path))

    if sys.platform == "win32":
        candidates.append(Path(r"C:\ffmpeg\bin\ffprobe.exe"))

    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    return None


def load_json(path: Path, errors: list[str], label: str) -> Any:
    try:
        with path.open("r", encoding="utf-8-sig") as file:
            return json.load(file)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        errors.append(f"{label}: invalid JSON or UTF-8 ({error})")
        return None


def is_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def check_jpeg(path: Path, errors: list[str], label: str) -> None:
    try:
        data = path.read_bytes()
    except OSError as error:
        errors.append(f"{label}: cannot read JPEG ({error})")
        return

    if len(data) <= 4 or data[:2] != b"\xff\xd8" or data[-2:] != b"\xff\xd9":
        errors.append(f"{label}: file is not a complete JPEG")


def measure_audio(
    audio_path: Path,
    ffprobe: Path,
    errors: list[str],
    label: str,
) -> float | None:
    try:
        result = subprocess.run(
            [
                str(ffprobe),
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(audio_path),
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        errors.append(f"{label}: ffprobe failed ({error})")
        return None

    if result.returncode != 0:
        detail = result.stderr.strip() or f"exit code {result.returncode}"
        errors.append(f"{label}: audio cannot be decoded ({detail})")
        return None

    try:
        duration = float(result.stdout.strip())
    except ValueError:
        errors.append(f"{label}: ffprobe returned no numeric duration")
        return None

    if not math.isfinite(duration) or duration <= 0:
        errors.append(f"{label}: invalid measured duration {duration!r}")
        return None
    return duration


def check_required_file(
    path: Path,
    errors: list[str],
    label: str,
) -> bool:
    if not path.is_file():
        errors.append(f"{label}: missing file")
        return False
    try:
        if path.stat().st_size <= 0:
            errors.append(f"{label}: file is empty")
            return False
    except OSError as error:
        errors.append(f"{label}: cannot inspect file ({error})")
        return False
    return True


def check_lesson(
    lesson_path: Path,
    course_data: dict[str, Any],
    expected_level: str,
    ffprobe: Path,
    errors: list[str],
) -> tuple[str | None, float | None]:
    lesson_label = str(lesson_path.name)
    required_files = list(BASE_LESSON_FILES)
    if course_data.get("has_lesson_images") is True:
        required_files.append("image.jpg")

    present: dict[str, bool] = {}
    for filename in required_files:
        present[filename] = check_required_file(
            lesson_path / filename,
            errors,
            f"{lesson_label}/{filename}",
        )

    mp3_files = sorted(
        path.name
        for path in lesson_path.iterdir()
        if path.is_file() and path.suffix.lower() == ".mp3"
    )
    if mp3_files != ["audio.mp3"]:
        errors.append(
            f"{lesson_label}: expected exactly one MP3 named audio.mp3; "
            f"found {mp3_files}"
        )

    image_path = lesson_path / "image.jpg"
    if course_data.get("has_lesson_images") is True and present.get("image.jpg"):
        check_jpeg(image_path, errors, f"{lesson_label}/image.jpg")

    description: Any = None
    if present.get("description.json"):
        description = load_json(
            lesson_path / "description.json",
            errors,
            f"{lesson_label}/description.json",
        )
    lesson_data: Any = None
    if present.get("lesson.json"):
        lesson_data = load_json(
            lesson_path / "lesson.json",
            errors,
            f"{lesson_label}/lesson.json",
        )
    timestamps: Any = None
    if present.get("timestamp.json"):
        timestamps = load_json(
            lesson_path / "timestamp.json",
            errors,
            f"{lesson_label}/timestamp.json",
        )

    lesson_number: str | None = None
    if not isinstance(description, dict):
        if description is not None:
            errors.append(f"{lesson_label}/description.json: root must be an object")
    else:
        missing_fields = sorted(LESSON_REQUIRED_FIELDS - description.keys())
        if missing_fields:
            errors.append(
                f"{lesson_label}/description.json: missing fields {missing_fields}"
            )

        raw_number = description.get("lesson_number")
        if raw_number is None or isinstance(raw_number, bool):
            errors.append(
                f"{lesson_label}/description.json: invalid lesson_number "
                f"{raw_number!r}"
            )
        else:
            lesson_number = str(raw_number)

        if not is_non_empty_string(description.get("lesson_name")):
            errors.append(
                f"{lesson_label}/description.json: lesson_name must be non-empty"
            )
        if description.get("level") != expected_level:
            errors.append(
                f"{lesson_label}/description.json: level "
                f"{description.get('level')!r} does not match folder "
                f"{expected_level!r}"
            )
        start_time = description.get("audio_start_time")
        if start_time is not None and not is_number(start_time):
            errors.append(
                f"{lesson_label}/description.json: audio_start_time must be "
                "a number or null"
            )
        if not is_number(description.get("audio_duration")) or float(
            description.get("audio_duration", 0)
        ) <= 0:
            errors.append(
                f"{lesson_label}/description.json: audio_duration must be "
                "a positive number"
            )
        if not isinstance(description.get("has_sentence_timestamps"), bool):
            errors.append(
                f"{lesson_label}/description.json: "
                "has_sentence_timestamps must be boolean"
            )

    if not isinstance(lesson_data, dict):
        if lesson_data is not None:
            errors.append(f"{lesson_label}/lesson.json: root must be an object")
    else:
        list_ref = lesson_data.get("list_ref")
        list_id = lesson_data.get("list_id")
        if not isinstance(list_ref, list) or not list_ref:
            errors.append(
                f"{lesson_label}/lesson.json: list_ref must be a non-empty list"
            )
        elif any(not isinstance(item, str) for item in list_ref):
            errors.append(
                f"{lesson_label}/lesson.json: every list_ref item must be a string"
            )
        if list_id is not None and not isinstance(list_id, list):
            errors.append(
                f"{lesson_label}/lesson.json: list_id must be a list when present"
            )
        if (
            isinstance(list_ref, list)
            and isinstance(list_id, list)
            and len(list_ref) != len(list_id)
        ):
            errors.append(
                f"{lesson_label}/lesson.json: list_ref/list_id lengths differ "
                f"({len(list_ref)} != {len(list_id)})"
            )

    if not isinstance(timestamps, list) or not timestamps:
        errors.append(
            f"{lesson_label}/timestamp.json: root must be a non-empty list"
        )

    measured: float | None = None
    if present.get("audio.mp3"):
        measured = measure_audio(
            lesson_path / "audio.mp3",
            ffprobe,
            errors,
            f"{lesson_label}/audio.mp3",
        )
        if measured is not None and isinstance(description, dict):
            declared = description.get("audio_duration")
            if is_number(declared) and round(float(declared), 2) != round(
                measured, 2
            ):
                errors.append(
                    f"{lesson_label}/description.json: audio_duration "
                    f"{declared!r} does not match measured "
                    f"{round(measured, 2)!r}"
                )

    return lesson_number, measured


def check_course(
    language: str,
    branch_root: Path,
    course_description: Path,
    ffprobe: Path,
) -> CourseResult:
    course_path = course_description.parents[1]
    relative_path = course_path.relative_to(branch_root)
    result = CourseResult(language=language, relative_path=relative_path)
    expected_level = relative_path.parts[0]

    course_data = load_json(
        course_description,
        result.errors,
        "course_infos/description.json",
    )
    if not isinstance(course_data, dict):
        if course_data is not None:
            result.errors.append(
                "course_infos/description.json: root must be an object"
            )
        return result

    missing_fields = sorted(COURSE_REQUIRED_FIELDS - course_data.keys())
    if missing_fields:
        result.errors.append(
            f"course_infos/description.json: missing fields {missing_fields}"
        )
    if not is_non_empty_string(course_data.get("course_name")):
        result.errors.append(
            "course_infos/description.json: course_name must be non-empty"
        )
    if course_data.get("content_language") != language:
        result.errors.append(
            "course_infos/description.json: content_language "
            f"{course_data.get('content_language')!r} does not match branch "
            f"{language!r}"
        )
    if not isinstance(course_data.get("type"), list):
        result.errors.append(
            "course_infos/description.json: type must be a JSON list"
        )
    if course_data.get("level") != expected_level:
        result.errors.append(
            "course_infos/description.json: level "
            f"{course_data.get('level')!r} does not match folder "
            f"{expected_level!r}"
        )
    if not is_number(course_data.get("audio_duration")) or float(
        course_data.get("audio_duration", 0)
    ) <= 0:
        result.errors.append(
            "course_infos/description.json: audio_duration must be a "
            "positive number"
        )
    if course_data.get("has_lesson_images") is not None and not isinstance(
        course_data.get("has_lesson_images"), bool
    ):
        result.errors.append(
            "course_infos/description.json: has_lesson_images must be "
            "boolean or null"
        )

    course_image = course_path / "course_infos" / "image.jpg"
    if check_required_file(
        course_image,
        result.errors,
        "course_infos/image.jpg",
    ):
        check_jpeg(course_image, result.errors, "course_infos/image.jpg")

    if course_data.get("avatar") == "avatar.jpg":
        avatar = course_path / "course_infos" / "avatar.jpg"
        if check_required_file(
            avatar,
            result.errors,
            "course_infos/avatar.jpg",
        ):
            check_jpeg(avatar, result.errors, "course_infos/avatar.jpg")

    lessons_path = course_path / "lessons"
    if not lessons_path.is_dir():
        result.errors.append("lessons: folder is missing")
        return result

    lesson_paths = sorted(
        (path for path in lessons_path.iterdir() if path.is_dir()),
        key=lambda path: path.name.casefold(),
    )
    result.lesson_count = len(lesson_paths)
    if not lesson_paths:
        result.errors.append("lessons: no lesson folders found")
        return result

    lesson_numbers: list[str] = []
    measured_total = 0.0
    all_audio_measured = True
    for lesson_path in lesson_paths:
        lesson_number, measured = check_lesson(
            lesson_path,
            course_data,
            expected_level,
            ffprobe,
            result.errors,
        )
        if lesson_number is not None:
            lesson_numbers.append(lesson_number)
        if measured is None:
            all_audio_measured = False
        else:
            measured_total += measured

    duplicate_numbers = sorted(
        number
        for number, count in Counter(lesson_numbers).items()
        if count > 1
    )
    if duplicate_numbers:
        result.errors.append(
            f"lessons: duplicate lesson_number values {duplicate_numbers}"
        )

    result.measured_duration = round(measured_total, 2)
    declared_course_duration = course_data.get("audio_duration")
    if (
        all_audio_measured
        and is_number(declared_course_duration)
        and round(float(declared_course_duration), 2)
        != result.measured_duration
    ):
        result.errors.append(
            "course_infos/description.json: audio_duration "
            f"{declared_course_duration!r} does not match measured lesson "
            f"total {result.measured_duration!r}"
        )

    return result


def check_branch(
    project_root: Path,
    language: str,
    ffprobe: Path,
) -> BranchResult:
    branch_root = project_root / language
    branch = BranchResult(language=language, root=branch_root)
    if not branch_root.is_dir():
        branch.errors.append(f"branch folder does not exist: {branch_root}")
        return branch

    expected_descriptions = sorted(
        branch_root.glob("*/*/course_infos/description.json"),
        key=lambda path: str(path).casefold(),
    )
    all_descriptions = sorted(
        branch_root.rglob("course_infos/description.json"),
        key=lambda path: str(path).casefold(),
    )
    unexpected = [
        path.relative_to(branch_root)
        for path in all_descriptions
        if path not in expected_descriptions
    ]
    for path in unexpected:
        branch.errors.append(
            f"course has unsupported nesting (expected <level>/<course>): {path}"
        )

    for level_path in sorted(
        (path for path in branch_root.iterdir() if path.is_dir()),
        key=lambda path: path.name.casefold(),
    ):
        if level_path.name.lower() not in LEVELS:
            continue
        for course_path in sorted(
            (path for path in level_path.iterdir() if path.is_dir()),
            key=lambda path: path.name.casefold(),
        ):
            description = course_path / "course_infos" / "description.json"
            if not description.is_file():
                branch.errors.append(
                    f"course folder is missing course_infos/description.json: "
                    f"{course_path.relative_to(branch_root)}"
                )

    if not expected_descriptions:
        branch.errors.append(
            "no courses found at <branch>/<level>/<course>/course_infos/description.json"
        )
        return branch

    for description in expected_descriptions:
        branch.courses.append(
            check_course(language, branch_root, description, ffprobe)
        )
    return branch


def print_results(results: list[BranchResult], ffprobe: Path) -> None:
    print(f"ffprobe: {ffprobe}")
    print("=" * 72)
    total_courses = 0
    total_lessons = 0
    total_errors = 0

    for branch in results:
        print(f"BRANCH {branch.language}: {branch.root}")
        for error in branch.errors:
            print(f"  [ERROR] {error}")
            total_errors += 1

        for course in branch.courses:
            total_courses += 1
            total_lessons += course.lesson_count
            status = "READY" if course.ready else "NOT READY"
            print(
                f"  [{status}] {course.relative_path} | "
                f"lessons={course.lesson_count} | "
                f"duration={course.measured_duration:.2f}s"
            )
            for error in course.errors:
                print(f"    - {error}")
                total_errors += 1

        branch_status = "READY" if branch.ready else "NOT READY"
        print(
            f"  Branch result: {branch_status} "
            f"({len(branch.courses)} course(s))"
        )
        print("-" * 72)

    overall_ready = all(result.ready for result in results)
    print(
        f"OVERALL: {'READY' if overall_ready else 'NOT READY'} | "
        f"courses={total_courses} | lessons={total_lessons} | "
        f"errors={total_errors}"
    )


def main() -> int:
    args = parse_arguments()
    project_root = args.project_root.expanduser().resolve()
    if not project_root.is_dir():
        print(f"ERROR: project root does not exist: {project_root}", file=sys.stderr)
        return 2

    ffprobe = find_ffprobe(args.ffprobe)
    if ffprobe is None:
        print(
            "ERROR: ffprobe was not found. Add it to PATH or pass "
            "--ffprobe C:\\path\\to\\ffprobe.exe",
            file=sys.stderr,
        )
        return 2

    languages = LANGUAGES if args.language == "all" else (args.language,)
    results = [
        check_branch(project_root, language, ffprobe)
        for language in languages
    ]
    print_results(results, ffprobe)
    return 0 if all(result.ready for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
