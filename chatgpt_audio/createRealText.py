import os
import re

# Path to your combined master text file
input_file = r"C:\Users\PC\Desktop\kaggle\whisper\chatgpt_audio\real_text.txt"

# Folder where the 20 topic files will be saved
output_dir = r"C:\Users\PC\Desktop\kaggle\whisper\chatgpt_audio\realText"

os.makedirs(output_dir, exist_ok=True)

with open(input_file, "r", encoding="utf-8") as f:
    text = f.read()

# Find each story block
pattern = r"### FILE:\s*(.+?\.txt)\s*\n(.*?)### END FILE"

matches = re.findall(pattern, text, flags=re.DOTALL)

print(f"Found {len(matches)} stories.")

for filename, content in matches:
    filename = filename.strip()
    content = content.strip()

    # Remove the TOPIC line
    content = re.sub(
        r"^### TOPIC:.*?\n+",
        "",
        content,
        flags=re.MULTILINE
    )

    content = content.strip()

    output_path = os.path.join(output_dir, filename)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content + "\n")

    print(f"Saved: {filename}")

print(f"\nDone. Created {len(matches)} files.")