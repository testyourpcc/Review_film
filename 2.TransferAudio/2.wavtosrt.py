import math
import os
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TRANSCRIBE_PROVIDER = os.getenv("TRANSCRIBE_PROVIDER", "local").lower()
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "large")
OPENAI_TRANSCRIBE_MODEL = os.getenv("OPENAI_TRANSCRIBE_MODEL", "whisper-1")


def convert_wav_to_srt(wav_file, output_srt_path, target_segments=50):
    if TRANSCRIBE_PROVIDER == "openai":
        convert_wav_to_srt_openai(wav_file, output_srt_path)
        return

    import whisper

    model = whisper.load_model(WHISPER_MODEL)
    result = model.transcribe(str(wav_file), word_timestamps=True)
    segments = result["segments"]

    if len(segments) <= target_segments:
        merged = segments
    else:
        batch_size = math.ceil(len(segments) / target_segments)
        merged = []
        for i in range(0, len(segments), batch_size):
            batch = segments[i:i + batch_size]
            start_time = batch[0]["start"]
            end_time = batch[-1]["end"]
            text = " ".join([seg["text"].strip() for seg in batch])
            merged.append({"start": start_time, "end": end_time, "text": text})

    srt_lines = []
    for idx, seg in enumerate(merged, start=1):
        srt_lines.append(f"{idx}")
        srt_lines.append(f"{fmt_time(seg['start'])} --> {fmt_time(seg['end'])}")
        srt_lines.append(seg["text"])
        srt_lines.append("")

    output_srt_path.parent.mkdir(parents=True, exist_ok=True)
    output_srt_path.write_text("\n".join(srt_lines), encoding="utf-8")
    print(f"Generated SRT with {len(merged)} segments at: {output_srt_path}")


def convert_wav_to_srt_openai(wav_file, output_srt_path):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY for OpenAI transcription.")

    with open(wav_file, "rb") as audio_file:
        response = requests.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {api_key}"},
            data={
                "model": OPENAI_TRANSCRIBE_MODEL,
                "response_format": "srt",
                "language": "zh",
            },
            files={"file": audio_file},
            timeout=600,
        )

    response.raise_for_status()
    output_srt_path.parent.mkdir(parents=True, exist_ok=True)
    output_srt_path.write_text(response.text, encoding="utf-8")
    print(f"Generated SRT with OpenAI transcription at: {output_srt_path}")


def fmt_time(ts):
    h = int(ts // 3600)
    m = int((ts % 3600) // 60)
    s = int(ts % 60)
    ms = int((ts - int(ts)) * 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


if __name__ == "__main__":
    wav = PROJECT_ROOT / "2.TransferAudio" / "outputwav" / "output.wav"
    out_srt = PROJECT_ROOT / "2.TransferAudio" / "srt" / "output.srt"
    convert_wav_to_srt(wav, out_srt, target_segments=50)
