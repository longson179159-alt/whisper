import os
import subprocess


DIR_PATH = r"C:\Users\PC\Desktop\kaggle\whisper\chatgpt_audio\en_easy_stories"
# convert audio from aac to mp3
def convert_aac_to_mp3(filePath):
    if not os.path.exists(filePath):
        raise FileNotFoundError(f"File not found: {filePath}")

    # Check if the file is an AAC file
    if not filePath.lower().endswith('.aac'):
        raise ValueError("The provided file is not an AAC file.")

    # Define the output MP3 file path
    mp3_file_path = os.path.splitext(filePath)[0] + '.mp3'

    # Convert the audio. `check=True` ensures the AAC is kept if FFmpeg fails.
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            filePath,
            "-codec:a",
            "libmp3lame",
            "-qscale:a",
            "2",
            mp3_file_path,
        ],
        check=True,
    )

    # Delete the source only after a successful conversion.
    os.remove(filePath)

    return mp3_file_path

if __name__ == "__main__":
    # Iterate through all files in the directory
    for filename in os.listdir(DIR_PATH):
        file_path = os.path.join(DIR_PATH, filename)
        if filename.lower().endswith('.aac'):
            try:
                mp3_file_path = convert_aac_to_mp3(file_path)
                print(f"Converted {file_path} to {mp3_file_path}")
            except Exception as e:
                print(f"Error converting {file_path}: {e}")
