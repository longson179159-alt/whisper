

import os
import yt_dlp


YOUTUBE_PLAYLIST_URL = "https://www.youtube.com/watch?v=hsPuBUVcc84&list=PLh8nsCd50fIk9-iI_HN-1D_QF6KGoqBQx&index=7"
# easy mandarin
# https://www.youtube.com/watch?v=hsPuBUVcc84&list=PLh8nsCd50fIk9-iI_HN-1D_QF6KGoqBQx&index=7
DIR_PATH = os.path.dirname(os.path.abspath(__file__))

OUTPUT_DIR = os.path.join(DIR_PATH, "easy_mandarin_playlist")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# download all audio from the playlist
ydl_opts = {
    'format': 'bestaudio/best',
    'outtmpl': os.path.join(OUTPUT_DIR, '%(title)s.%(ext)s'),
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    ydl.download([YOUTUBE_PLAYLIST_URL])

