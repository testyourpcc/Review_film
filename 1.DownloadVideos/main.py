from pathlib import Path

import download
import videos

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Ví dụ sử dụng
if __name__ == "__main__":
    file_path = PROJECT_ROOT / "1.DownloadVideos" / "videourls.txt"
    download_video_path = PROJECT_ROOT / "1.DownloadVideos" / "output_link_video.txt"
    chromedriver_path = PROJECT_ROOT / "driver" / "chromedriver.exe"
    downloaded_folder = PROJECT_ROOT / "1.DownloadVideos" / "output"
    
    download.url_videos(file_path, chromedriver_path)
    videos.download_videos_from_file(download_video_path, downloaded_folder)
