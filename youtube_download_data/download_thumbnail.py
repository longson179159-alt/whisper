from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen


OUTPUT_PATH = Path(__file__).resolve().with_name("image.jpg")


def get_video_id(url: str) -> str:
    """Extract a video ID from a standard YouTube or youtu.be URL."""
    parsed_url = urlparse(url)
    if parsed_url.netloc.lower().endswith("youtu.be"):
        video_id = parsed_url.path.strip("/").split("/")[0]
    else:
        video_id = parse_qs(parsed_url.query).get("v", [""])[0]

    if not video_id:
        raise ValueError(f"Could not find a YouTube video ID in: {url}")
    return video_id


def download_thumbnail(url: str, destination: Path) -> Path:
    """Download the best available official JPEG thumbnail for a YouTube video."""
    video_id = get_video_id(url)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": "Mozilla/5.0 (thumbnail downloader)"}

    for image_name in (
        "maxresdefault.jpg",
        "sddefault.jpg",
        "hqdefault.jpg",
        "mqdefault.jpg",
    ):
        thumbnail_url = f"https://i.ytimg.com/vi/{video_id}/{image_name}"
        request = Request(thumbnail_url, headers=headers)
        try:
            with urlopen(request, timeout=30) as response:
                data = response.read()
        except HTTPError as error:
            if error.code == 404:
                continue
            raise RuntimeError(
                f"HTTP {error.code} while requesting {thumbnail_url}"
            ) from error
        except URLError as error:
            raise RuntimeError(
                f"Could not download {thumbnail_url}: {error.reason}"
            ) from error

        destination.write_bytes(data)
        print(f"Saved {image_name} to: {destination}")
        return destination

    raise RuntimeError(f"No official JPEG thumbnail was available for video {video_id}.")


if __name__ == "__main__":
    url = "https://www.youtube.com/watch?v=fxvOPdOYyeo&t=6683s"
    download_thumbnail(url, OUTPUT_PATH)
