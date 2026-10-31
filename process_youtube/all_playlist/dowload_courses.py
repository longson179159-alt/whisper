"""Create a course from the individual YouTube URLs in ``peding.txt``."""

from __future__ import annotations

from pathlib import Path

from yt_dlp.utils import DownloadError

from download_youtube_playlist import PROJECT_DIR, download_lesson, safe_title


URL_FILE = Path(__file__).resolve().with_name("peding.txt")


def read_urls(url_file: Path = URL_FILE) -> list[str]:
    """Read non-empty, non-comment URL lines in their original order."""
    return [
        line.strip()
        for line in url_file.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def build_course(output_name: str) -> None:
    urls = read_urls()
    if not urls:
        raise ValueError(f"No YouTube URLs found in {URL_FILE}")

    course_name = safe_title(output_name, max_length=60)
    output_dir = PROJECT_DIR / "en" / course_name / "LESSONS"
    output_dir.mkdir(parents=True, exist_ok=True)

    failures: list[tuple[int, str]] = []
    for index, url in enumerate(urls, start=1):
        try:
            download_lesson(index, url, output_dir)
        except DownloadError as error:
            failures.append((index, url))
            print(f"[{index}] Download failed: {error}")

    successful = len(urls) - len(failures)
    print(f"\nFinished: {successful}/{len(urls)} lessons downloaded")
    print(f"Course folder: {output_dir.resolve()}")
    if failures:
        print("Failed URLs:")
        for index, url in failures:
            print(f"  {index}. {url}")


def main() -> None:
    output_name = input("Output/course name: ").strip()
    if not output_name:
        raise ValueError("Output/course name cannot be blank")
    build_course(output_name)


if __name__ == "__main__":
    main()
