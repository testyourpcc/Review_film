import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

video_path = PROJECT_ROOT / "1.DownloadVideos" / "output" / "1.mp4"
audio_path = PROJECT_ROOT / "2.TransferAudio" / "outputwav" / "output.wav"
output_video_path = PROJECT_ROOT / "2.TransferAudio" / "videonosounds" / "videonosounds.mp4"

audio_path.parent.mkdir(parents=True, exist_ok=True)
output_video_path.parent.mkdir(parents=True, exist_ok=True)

subprocess.run([
    "ffmpeg", "-y",
    "-i", str(video_path),
    "-vn",
    "-acodec", "pcm_s16le",
    "-ar", "16000",
    "-ac", "1",
    str(audio_path),
], check=True)

subprocess.run([
    "ffmpeg", "-y",
    "-i", str(video_path),
    "-an",
    "-c:v", "copy",
    str(output_video_path),
], check=True)

print(f"Audio saved to: {audio_path}")
print(f"Video without audio saved to: {output_video_path}")
