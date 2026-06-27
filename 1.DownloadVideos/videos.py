import requests
import os

def download_video(video_url, save_path):
    try:
        # Keep console messages ASCII-only so this also works in legacy
        # Windows terminals configured with cp1252 instead of UTF-8.
        print(f"Downloading media from: {video_url}")
        with requests.get(video_url, stream=True, timeout=120) as response:
            response.raise_for_status()
            with open(save_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        file.write(chunk)
        print(f"Media download complete: {save_path}")
    except Exception as exc:
        print(f"Media download failed: {exc!r}")
        raise

def download_videos_from_file(file_path, download_folder):
    # Đọc danh sách các URL từ file
    with open(file_path, 'r') as file:
        video_urls = file.read().splitlines()

    # Tạo thư mục tải video nếu chưa tồn tại
    if not os.path.exists(download_folder):
        os.makedirs(download_folder)

    # Lặp qua từng URL trong danh sách và tải video
    for index, video_url in enumerate(video_urls, start=1):  # start=1 để bắt đầu từ 1
        save_path = os.path.join(download_folder, f"{index}.mp4")  # Đặt tên video là 1.mp4, 2.mp4, ...
        download_video(video_url, save_path)
