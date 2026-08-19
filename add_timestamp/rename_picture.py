
import os


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


CURRENT_FOLDER = 'listen_a_minute'
CURRENT_FOLDER_PATH = os.path.join(PROJECT_ROOT, 'en', CURRENT_FOLDER)  # Path to the folder containing the text and raw timestamp files.

def main():
    renamed_pictures = []

    for folder_name in sorted(os.listdir(CURRENT_FOLDER_PATH)):
        folder_path = os.path.join(CURRENT_FOLDER_PATH, folder_name)
        if not os.path.isdir(folder_path):
            continue

        # rename the picture to 'image.png'
        # get the picture file in the folder
        picture_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.png')]
        if picture_files:
            picture_file = picture_files[0]  # take the first picture file found
            old_picture_path = os.path.join(folder_path, picture_file)
            new_picture_path = os.path.join(folder_path, 'image.png')
            os.rename(old_picture_path, new_picture_path)
            renamed_pictures.append(new_picture_path)


        # rename the audio to 'audio.mp3'
        audio_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.mp3')]
        if audio_files:
            audio_file = audio_files[0]  # take the first audio file found
            old_audio_path = os.path.join(folder_path, audio_file)
            new_audio_path = os.path.join(folder_path, 'audio.mp3')
            os.rename(old_audio_path, new_audio_path)

    print("Renamed pictures:")
    for picture_path in renamed_pictures:
        print(f"Renamed to {os.path.basename(picture_path)} in {os.path.dirname(picture_path)}")
    print("Renamed audio files:")
    for audio_path in audio_files:
        print(f"Renamed to {os.path.basename(audio_path)} in {os.path.dirname(audio_path)}")

if __name__ == "__main__":
    main()