from __future__ import annotations

import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse, parse_qs
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_PATH = PROJECT_ROOT / "image.jpg"


def download_thumbnail(video_id: str, destination: Path) -> str:
    """Download the best available YouTube thumbnail."""

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    # Try highest quality first
    for image_name in (
        "maxresdefault.jpg",
        "sddefault.jpg",
        "hqdefault.jpg",
        "mqdefault.jpg",
    ):
        url = f"https://img.youtube.com/vi/{video_id}/{image_name}"

        request = Request(url, headers=headers)

        try:
            with urlopen(request, timeout=30) as response:
                data = response.read()

        except HTTPError as error:
            if error.code == 404:
                continue

            raise RuntimeError(
                f"HTTP {error.code} while requesting {url}"
            ) from error

        except URLError as error:
            raise RuntimeError(
                f"Could not download {url}: {error.reason}"
            ) from error

        # Sometimes YouTube returns a small placeholder
        if len(data) < 1000:
            continue

        destination.write_bytes(data)

        return image_name

    raise RuntimeError(
        "YouTube did not provide a downloadable thumbnail"
    )


def main(url: str, output_path: Path = OUTPUT_PATH):
    """Download a YouTube video's thumbnail."""

    parsed_url = urlparse(url)

    query = parse_qs(parsed_url.query)

    video_id = query.get("v", [None])[0]

    if not video_id:
        raise ValueError(f"Invalid YouTube URL: {url}")

    try:
        image_name = download_thumbnail(
            video_id,
            output_path
        )

    except RuntimeError as error:
        print(
            f"Failed to download thumbnail for {url}: {error}",
            file=sys.stderr,
        )
        return

    print(
        f"Downloaded {image_name} "
        f"for video {video_id} "
        f"to {output_path}"
    )


if __name__ == "__main__":
    url = "https://www.youtube.com/watch?v=MhwNZ5crpBw"

    main(url)