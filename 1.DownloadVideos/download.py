from Downloader import VideoURLExtractor

def url_videos(file_path, chromedriver_path):
    # Đọc các URL từ file
    with open(file_path, 'r') as file:
        list_video_urls = file.read().splitlines()

    # Lặp qua từng URL và tải video
    for url in list_video_urls:  # Không cần sử dụng enumerate
        downloader = VideoURLExtractor(video_url=url, chromedriver_path=chromedriver_path)
        downloader.run()
