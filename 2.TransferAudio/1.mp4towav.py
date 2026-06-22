from moviepy import VideoFileClip
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

video_path = PROJECT_ROOT / "1.DownloadVideos" / "output" / "1.mp4"
audio_path = PROJECT_ROOT / "2.TransferAudio" / "outputwav" / "output.wav"  # Đặt tên đầy đủ và mở rộng file
output_video_path = PROJECT_ROOT / "2.TransferAudio" / "videonosounds" / "videonosounds.mp4"  # Đặt tên đầy đủ và mở rộng file

audio_path.parent.mkdir(parents=True, exist_ok=True)
output_video_path.parent.mkdir(parents=True, exist_ok=True)

# Tách âm thanh từ video và lưu thành file WAV
video = VideoFileClip(str(video_path))
audio = video.audio
audio.write_audiofile(str(audio_path), codec='pcm_s16le')  # Lưu dưới dạng WAV

# Xóa âm thanh trong video và lưu lại video mới không có âm thanh
video_without_audio = video.without_audio()
video_without_audio.write_videofile(str(output_video_path), codec='libx264', audio_codec='aac')

print(f"Đã tách âm thanh và lưu thành file: {audio_path}")
print(f"Đã xóa âm thanh khỏi video và lưu thành file: {output_video_path}")


