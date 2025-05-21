import os
import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium_stealth import stealth


class VideoURLExtractor:
    def __init__(self, video_url, chromedriver_path):
        self.video_url = video_url
        self.chromedriver_path = chromedriver_path
        self.file_path = os.path.join(os.getcwd(), r'C:\Users\ngodu\Desktop\Videos\1.DownloadVideos\output_link_video.txt')
        self.driver = None

    def setup_driver(self):
        chrome_options = Options()
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_experimental_option("detach", True)
        chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

        service = Service(self.chromedriver_path)
        self.driver = webdriver.Chrome(service=service, options=chrome_options)

        stealth(self.driver,
                languages=["en-US", "en"],
                vendor="Google Inc.",
                platform="Win32",
                webgl_vendor="Intel Inc.",
                renderer="Intel Iris OpenGL Engine",
                fix_hairline=True,
                )

    def write_header(self):
        WebDriverWait(self.driver, 30).until(
            lambda driver: driver.execute_script("return document.readyState") == "complete"
        )
        time.sleep(2)

        logs = self.driver.get_log('performance')

        with open(self.file_path, 'w', encoding='utf-8') as file:  # Chế độ 'a' thay vì 'w'
            for log in logs:
                log_json = json.loads(log['message'])['message']
                method = log_json.get('method')
                if method in ['Network.requestWillBeSent', 'Network.responseReceived']:
                    try:
                        data = log_json['params']
                        request_or_response = data.get('request', data.get('response', {}))
                        url = request_or_response.get('url', '')
                        if '/video/tos' in url:  # Chỉ lấy URL có '/video/tos'
                            file.write(f"{url}\n")  # Thêm URL mới vào cuối file
                            break  # Dừng sau khi tìm thấy URL đầu tiên
                    except Exception:
                        continue
        print(f"✅ Video URLs saved to: {self.file_path}")


    def run(self):
        self.setup_driver()

        # Truy cập vào trang video
        self.driver.get(self.video_url)

        # Lưu các URL video vào file
        self.write_header()

        # Đóng trình duyệt
        self.driver.quit()
