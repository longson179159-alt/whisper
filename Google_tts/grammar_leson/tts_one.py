from google.cloud import texttospeech
from pydub import AudioSegment
from io import BytesIO
from pathlib import Path


# This demo generates audio for only the first grammar lesson.
BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "text" / "1.The New Neighbor.txt"
OUTPUT_DIR = BASE_DIR / "tts_output"
OUTPUT_FILE = OUTPUT_DIR / f"{INPUT_FILE.stem}.mp3"

VOICES = {
    "Narrator": "en-US-Chirp3-HD-Iapetus",
    "Emma": "en-US-Chirp3-HD-Leda",
    "Jack": "en-US-Chirp3-HD-Puck",
}

SPEAKING_RATE = 1.0
DIALOGUE_PAUSE_MS = 450
TITLE_PAUSE_MS = 1500
NARRATOR_TARGET_DBFS = -16.0
PEAK_HEADROOM_DB = 1.0


def read_dialogue():
    dialogue = []

    with open(INPUT_FILE, "r", encoding="utf-8-sig") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            # The narrator reads both the title and grammar description.
            if line.lower().startswith(("lesson ", "grammar:")):
                dialogue.append(("Narrator", line))
                continue

            if ":" not in line:
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


def main():
    if not INPUT_FILE.is_file():
        raise FileNotFoundError(f"Input file not found: {INPUT_FILE}")

    dialogue = read_dialogue()

    if not dialogue:
        raise ValueError(f"No dialogue found in: {INPUT_FILE}")

    client = texttospeech.TextToSpeechClient()
    OUTPUT_DIR.mkdir(exist_ok=True)

    combined_audio = AudioSegment.empty()
    dialogue_pause = AudioSegment.silent(duration=DIALOGUE_PAUSE_MS)
    title_pause = AudioSegment.silent(duration=TITLE_PAUSE_MS)

    print(f"Processing: {INPUT_FILE.name}")

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

    combined_audio.export(OUTPUT_FILE, format="mp3")

    print(f"\nSuccess! Created: {OUTPUT_FILE}")
    print(f"Duration: {len(combined_audio) / 1000:.1f} seconds")


if __name__ == "__main__":
    main()
