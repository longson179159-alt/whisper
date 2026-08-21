import yt_dlp

playlist_url = "https://www.youtube.com/playlist?list=PLAg1DP01xg5sU4zphvEWWiN_hbv5bL7gG"
video_id = "i-C4-Tbfl3g"

ydl_opts = {
    "quiet": True,
    "extract_flat": True,
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info(playlist_url, download=False)

for index, video in enumerate(info["entries"], start=1):
    if video["id"] == video_id:
        print(index)
        break