from pathlib import Path
import re

folder = Path(r"C:\path\to\greeting_audio")

for file in folder.glob("*.mp3"):
    new_name = re.sub(r"[^a-zA-Z0-9._-]", "_", file.name)
    if new_name != file.name:
        file.rename(file.with_name(new_name))