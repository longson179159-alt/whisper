"""Rename lesson folders whose names contain Kaggle-forbidden brackets.

Examples:
    A1 [with Brian and Emily] -> A1 (with Brian and Emily)

Run this script without arguments to rename the immediate subfolders in
``en/English A1/lessons``. Use ``--dry-run`` to preview the changes first.
"""

from __future__ import annotations

import argparse
from pathlib import Path


DEFAULT_LESSONS_DIR = (
    Path(__file__).resolve().parents[1] / "en" / "English A1" / "lessons"
)


def kaggle_safe_name(name: str) -> str:
    """Replace square brackets while preserving the text inside them."""
    return name.replace("[", "(").replace("]", ")")


def rename_lesson_folders(lessons_dir: Path, dry_run: bool = False) -> int:
    if not lessons_dir.is_dir():
        raise FileNotFoundError(f"Lessons directory does not exist: {lessons_dir}")

    changes = [
        (folder, folder.with_name(kaggle_safe_name(folder.name)))
        for folder in lessons_dir.iterdir()
        if folder.is_dir() and kaggle_safe_name(folder.name) != folder.name
    ]

    # Compare case-insensitively because the intended environment is Windows.
    destination_keys = [destination.name.casefold() for _, destination in changes]
    if len(destination_keys) != len(set(destination_keys)):
        raise FileExistsError("Two folders would be renamed to the same name.")

    source_keys = {source.name.casefold() for source, _ in changes}
    for _, destination in changes:
        if destination.exists() and destination.name.casefold() not in source_keys:
            raise FileExistsError(f"Destination already exists: {destination}")

    if not changes:
        print("No folder names need to be changed.")
        return 0

    for source, destination in changes:
        prefix = "Would rename" if dry_run else "Renaming"
        print(f'{prefix}: "{source.name}" -> "{destination.name}"')
        if not dry_run:
            source.rename(destination)

    print(f"{'Found' if dry_run else 'Renamed'} {len(changes)} folder(s).")
    return len(changes)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Replace [ and ] in immediate lesson-folder names."
    )
    parser.add_argument(
        "lessons_dir",
        nargs="?",
        type=Path,
        default=DEFAULT_LESSONS_DIR,
        help=f"Lessons directory (default: {DEFAULT_LESSONS_DIR})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show proposed changes without renaming anything.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    rename_lesson_folders(arguments.lessons_dir.resolve(), arguments.dry_run)
