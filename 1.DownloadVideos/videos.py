import requests
import os

def download_video(video_url, save_path):
    try:
        # Gửi yêu cầu GET để tải video
        print(f"⏳ Đang tải video từ: {video_url}")
        response = requests.get(video_url, stream=True)

        # Kiểm tra nếu yêu cầu thành công (status code 200)
        if response.status_code == 200:
            # Mở file ở chế độ ghi nhị phân và lưu video
            with open(save_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):  # Dùng chunk_size để tải file lớn
                    file.write(chunk)
            print(f"✅ Video đã được tải về thành công: {save_path}")
        else:
            print(f"❌ Không thể tải video. Mã lỗi: {response.status_code}")
    except Exception as e:
        print(f"⚠️ Đã xảy ra lỗi khi tải video: {e}")

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
