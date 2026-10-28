
from google.cloud import texttospeech
from pydub import AudioSegment
from io import BytesIO
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "greeting"

# Google Cloud TTS
client = texttospeech.TextToSpeechClient()

VOICES = {
    "Narrator": "en-US-Chirp3-HD-Iapetus",
    "Anna": "en-US-Chirp3-HD-Aoede",
    "Tom": "en-US-Chirp3-HD-Achird",
}

# Audio settings
SPEAKING_RATE = 1.0
DIALOGUE_PAUSE_MS = 450
TITLE_PAUSE_MS = 1500
NARRATOR_TARGET_DBFS = -16.0
PEAK_HEADROOM_DB = 1.0

def read_dialogue(input_file):
    dialogue = []

    with open(input_file, "r", encoding="utf-8-sig") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            # Read lesson titles and unlabelled narration with Narrator.
            if line.lower().startswith("lesson ") or ":" not in line:
                dialogue.append(("Narrator", line))
                continue

            speaker, text = line.split(":", 1)
            speaker = speaker.strip()
            text = text.strip()

            if speaker not in VOICES:
                raise ValueError(
                    f"Unknown speaker at line {line_number}: {speaker}"
                )

            if text:
                dialogue.append((speaker, text))

    return dialogue


def generate_lesson(input_file):
    dialogue = read_dialogue(input_file)

    if not dialogue:
        print(f"Skipped empty file: {input_file.name}")
        return False

    output_file = BASE_DIR / f"tts_output/{input_file.stem}.mp3"
    combined_audio = AudioSegment.empty()
    dialogue_pause = AudioSegment.silent(duration=DIALOGUE_PAUSE_MS)
    title_pause = AudioSegment.silent(duration=TITLE_PAUSE_MS)

    print(f"\nProcessing: {input_file.name}")

    for index, (speaker, text) in enumerate(dialogue, start=1):
        print(f"[{index}/{len(dialogue)}] {speaker}: {text}")

        response = client.synthesize_speech(
            input=texttospeech.SynthesisInput(text=text),
            voice=texttospeech.VoiceSelectionParams(
                language_code="en-US",
                name=VOICES[speaker],
            ),
            audio_config=texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=SPEAKING_RATE,
            ),
        )

        segment = AudioSegment.from_file(
            BytesIO(response.audio_content),
            format="mp3",
        )

        if speaker == "Narrator" and segment.dBFS != float("-inf"):
            target_gain = NARRATOR_TARGET_DBFS - segment.dBFS

            if target_gain > 0:
                max_safe_gain = -PEAK_HEADROOM_DB - segment.max_dBFS
                target_gain = min(target_gain, max_safe_gain)

            if target_gain != 0:
                segment = segment.apply_gain(target_gain)

        combined_audio += segment

        if index < len(dialogue):
            is_title = (
                speaker == "Narrator"
                and text.lower().startswith("lesson ")
            )
            combined_audio += title_pause if is_title else dialogue_pause

    combined_audio.export(output_file, format="mp3")

    print(f"Success! Created: {output_file}")
    print(f"Duration: {len(combined_audio) / 1000:.1f} seconds")
    return True


def lesson_sort_key(path):
    prefix = path.name.split(".", 1)[0]
    lesson_number = int(prefix) if prefix.isdigit() else float("inf")
    return lesson_number, path.name.lower()


input_files = sorted(INPUT_DIR.glob("*.txt"), key=lesson_sort_key)

if not input_files:
    raise ValueError(f"No text files found in: {INPUT_DIR}")

created_count = 0

for input_file in input_files:
    try:
        if generate_lesson(input_file):
            created_count += 1
    except ValueError as error:
        print(f"Error in {input_file.name}: {error}")

print(f"\nFinished! Created {created_count} MP3 file(s).")
