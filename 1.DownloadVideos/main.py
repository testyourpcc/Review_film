import download, videos, os

# Ví dụ sử dụng
if __name__ == "__main__":
    file_path = r'C:\Users\ngodu\Desktop\Videos\1.DownloadVideos\videourls.txt'
    download_video_path = r"C:\Users\ngodu\Desktop\Videos\1.DownloadVideos\output_link_video.txt"
    chromedriver_path = r'C:\Users\ngodu\Desktop\Videos\driver\chromedriver.exe'
    downloaded_folder = r'C:\Users\ngodu\Desktop\Videos\1.DownloadVideos\output'
    
    download.url_videos(file_path, chromedriver_path)
    videos.download_videos_from_file(download_video_path, downloaded_folder)