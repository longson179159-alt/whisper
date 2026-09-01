import os
import json
import yt_dlp

PLAYLIST_ID = "PLcetZ6gSk969oGvAI0e4_PgVnlGbm64bp"
YOUTUBE_PLAYLIST_URL = f"https://www.youtube.com/playlist?list={PLAYLIST_ID}"

DIR_PATH = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(DIR_PATH, "list_urls.json")

ydl_opts = {
    "extract_flat": True,
    "quiet": False,          # show errors while testing
    "noplaylist": False,
    "ignoreconfig": True,    # prevent a global --no-playlist setting
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    playlist_info = ydl.extract_info(YOUTUBE_PLAYLIST_URL, download=False)

entries = playlist_info.get("entries")
if not entries:
    raise RuntimeError(
        f"Playlist entries were not returned. Type: {playlist_info.get('_type')}; "
        f"title: {playlist_info.get('title')}"
    )

videos = []
for index, video in enumerate(entries, start=1):
    if not video or not video.get("id"):
        continue

    video_id = video["id"]
    videos.append({
        "name": video.get("title", "Untitled"),
        "index": index,
        "id": video_id,
        "url": f"https://www.youtube.com/watch?v={video_id}",
    })

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(videos, f, ensure_ascii=False, indent=2)

print(f"Saved {len(videos)} video URLs to: {OUTPUT_PATH}")