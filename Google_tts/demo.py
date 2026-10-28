
from google.cloud import texttospeech
from pydub import AudioSegment
from io import BytesIO
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "1.Hello.txt"
OUTPUT_FILE = BASE_DIR / "1.Hello.mp3"

# Google Cloud TTS
client = texttospeech.TextToSpeechClient()

VOICES = {
    "Anna": "en-US-Chirp3-HD-Aoede",
    "Tom": "en-US-Chirp3-HD-Achird",
}

# Audio settings
SPEAKING_RATE = 1.0
PAUSE_MS = 450

# Read dialogue
dialogue = []

with open(INPUT_FILE, "r", encoding="utf-8-sig") as file:
    for line_number, line in enumerate(file, start=1):
        line = line.strip()

        if not line or line.startswith("#"):
            continue

        if ":" not in line:
            raise ValueError(
                f"Invalid format at line {line_number}: {line}"
            )

        speaker, text = line.split(":", 1)
        speaker = speaker.strip()
        text = text.strip()

        if speaker not in VOICES:
            raise ValueError(
                f"Unknown speaker at line {line_number}: {speaker}"
            )

        if text:
            dialogue.append((speaker, text))

if not dialogue:
    raise ValueError("No dialogue found in the text file.")

# Generate audio
combined_audio = AudioSegment.empty()
pause = AudioSegment.silent(duration=PAUSE_MS)

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

    if index > 1:
        combined_audio += pause

    combined_audio += segment

# Export MP3
combined_audio.export(OUTPUT_FILE, format="mp3")

print(f"\nSuccess! Created: {OUTPUT_FILE}")
print(f"Duration: {len(combined_audio) / 1000:.1f} seconds")
