import os

def remove_files(file_paths):
    for path in file_paths:
        try:
            if os.path.isfile(path):
                os.remove(path)
                print(f"Đã xóa: {path}")
            else:
                print(f"Không tìm thấy file: {path}")
        except Exception as e:
            print(f"Lỗi khi xóa {path}: {e}")

if __name__ == "__main__":
    # Danh sách các đường dẫn tới file cần xóa
    files_to_delete = [
        r"C:\Users\ngodu\Desktop\Videos\2.TransferAudio\ouputsounds\output.mp3",
        r"C:\Users\ngodu\Desktop\Videos\2.TransferAudio\outputwav\output.wav",
        r"C:\Users\ngodu\Desktop\Videos\2.TransferAudio\srt\output.srt",
        r"C:\Users\ngodu\Desktop\Videos\1.DownloadVideos\output\1.mp4",
        r"C:\Users\ngodu\Desktop\Videos\2.TransferAudio\videonosounds\videonosounds.mp4"
    ]

    remove_files(files_to_delete)
