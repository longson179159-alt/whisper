"""Download YouTube thumbnails for every Zoe Languages video.

Run from this directory or any other directory:

    python thumbnail.py

Each video's thumbnail is saved as ``image.jpg`` in the same folder as
its ``description.json``. Existing files are left untouched unless ``--force``
is supplied.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


# SCRIPT_DIR = Path(__file__).resolve().parent
# LESSONS_DIR = SCRIPT_DIR
THUMBNAIL_NAME = "image.jpg"


PROJECT_ROOT = Path(__file__).resolve().parent.parent
LESSONS_DIR = PROJECT_ROOT / "youtube_data" / "zoe_languages" / "lessons"



def download_thumbnail(video_id: str, destination: Path) -> str:
    """Download the first available official JPEG thumbnail variant.

    The variants are tried in the order below. YouTube does not create every
    size for every video, so later variants act as fallbacks.
    """
    headers = {"User-Agent": "Mozilla/5.0 (thumbnail downloader)"}
    for image_name in ("mqdefault.jpg", "hqdefault.jpg", "sddefault.jpg", "maxresdefault.jpg"):
        url = f"https://i.ytimg.com/vi/{video_id}/{image_name}"
        request = Request(url, headers=headers)
        try:
            with urlopen(request, timeout=30) as response:
                data = response.read()
        except HTTPError as error:
            if error.code == 404:
                continue
            raise RuntimeError(f"HTTP {error.code} while requesting {url}") from error
        except URLError as error:
            raise RuntimeError(f"Could not download {url}: {error.reason}") from error

        # A missing image can occasionally be returned as a tiny placeholder.
        if len(data) < 1_000:
            continue

        destination.write_bytes(data)
        return image_name

    raise RuntimeError("YouTube did not provide a downloadable thumbnail")


def process_lesson(description_path: Path, force: bool) -> str:
    destination = description_path.parent / THUMBNAIL_NAME
    if destination.exists() and not force:
        return "skipped (already exists)"

    try:
        metadata = json.loads(description_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return f"failed ({error})"

    video_id = metadata.get("youtube_id")
    if not isinstance(video_id, str) or len(video_id) != 11:
        return "failed (missing valid string 'youtube_id')"

    try:
        variant = download_thumbnail(video_id, destination)
    except (OSError, RuntimeError) as error:
        return f"failed ({error})"
    return f"downloaded ({variant})"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="replace thumbnails that are already present",
    )
    args = parser.parse_args()

    description_paths = sorted(LESSONS_DIR.glob("*/description.json"))
    if not description_paths:
        print(f"No description.json files found in {LESSONS_DIR}", file=sys.stderr)
        return 1

    failures = 0
    for description_path in description_paths:
        result = process_lesson(description_path, args.force)
        print(f"{description_path.parent.name}: {result}")
        failures += result.startswith("failed")

    print(f"\\nProcessed {len(description_paths)} lessons; {failures} failed.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
