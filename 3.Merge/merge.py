import ffmpeg
import os
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Đường dẫn thư mục và tên file gốc
output_folder = PROJECT_ROOT / "4.Final"
video_path = PROJECT_ROOT / "2.TransferAudio" / "videonosounds" / "videonosounds.mp4"
audio_path = PROJECT_ROOT / "2.TransferAudio" / "ouputsounds" / "output.mp3"

# Tìm số lớn nhất hiện có trong folder
def get_next_output_filename(folder):
    folder.mkdir(parents=True, exist_ok=True)
    files = os.listdir(folder)
    numbers = []
    for f in files:
        match = re.match(r'(\d+)\.mp4$', f)
        if match:
            numbers.append(int(match.group(1)))
    next_number = max(numbers) + 1 if numbers else 1
    return folder / f"{next_number}.mp4"

# Tạo output path mới
output_path = get_next_output_filename(output_folder)

# Ghép video và audio
ffmpeg \
    .output(
        ffmpeg.input(str(video_path)).video,
        ffmpeg.input(str(audio_path)).audio,
        str(output_path),
        vcodec='copy',
        acodec='aac',
        strict='experimental'
    ) \
    .run()

print(f"Final video created: {output_path}")
