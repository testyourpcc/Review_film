from moviepy import VideoFileClip


video_path = r"C:\Users\ngodu\Desktop\Videos\1.DownloadVideos\output\1.mp4"
audio_path = r"C:\Users\ngodu\Desktop\Videos\2.TransferAudio\outputwav\output.wav"  # Đặt tên đầy đủ và mở rộng file
output_video_path = r"C:\Users\ngodu\Desktop\Videos\2.TransferAudio\videonosounds\videonosounds.mp4"  # Đặt tên đầy đủ và mở rộng file

# Tách âm thanh từ video và lưu thành file WAV
video = VideoFileClip(video_path)
audio = video.audio
audio.write_audiofile(audio_path, codec='pcm_s16le')  # Lưu dưới dạng WAV

# Xóa âm thanh trong video và lưu lại video mới không có âm thanh
video_without_audio = video.without_audio()
video_without_audio.write_videofile(output_video_path, codec='libx264', audio_codec='aac')

print(f"Đã tách âm thanh và lưu thành file: {audio_path}")
print(f"Đã xóa âm thanh khỏi video và lưu thành file: {output_video_path}")


