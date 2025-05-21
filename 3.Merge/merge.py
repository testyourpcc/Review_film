import ffmpeg
import os
import re

# Đường dẫn thư mục và tên file gốc
output_folder = r'C:\Users\ngodu\Desktop\Videos\4.Final'
video_path = r'C:\Users\ngodu\Desktop\Videos\2.TransferAudio\videonosounds\videonosounds.mp4'
audio_path = r'C:\Users\ngodu\Desktop\Videos\2.TransferAudio\ouputsounds\output.mp3'

# Tìm số lớn nhất hiện có trong folder
def get_next_output_filename(folder):
    files = os.listdir(folder)
    numbers = []
    for f in files:
        match = re.match(r'(\d+)\.mp4$', f)
        if match:
            numbers.append(int(match.group(1)))
    next_number = max(numbers) + 1 if numbers else 1
    return os.path.join(folder, f"{next_number}.mp4")

# Tạo output path mới
output_path = get_next_output_filename(output_folder)

# Ghép video và audio
ffmpeg \
    .output(
        ffmpeg.input(video_path).video,
        ffmpeg.input(audio_path).audio,
        output_path,
        vcodec='copy',
        acodec='aac',
        strict='experimental'
    ) \
    .run()

print(f"✅ Xuất video hoàn tất: {output_path}")
