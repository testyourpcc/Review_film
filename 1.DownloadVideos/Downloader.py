import json
import time
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium_stealth import stealth

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class VideoURLExtractor:
    def __init__(self, video_url, chromedriver_path):
        self.video_url = video_url
        self.chromedriver_path = str(chromedriver_path)
        self.file_path = PROJECT_ROOT / "1.DownloadVideos" / "output_link_video.txt"
        self.driver = None

    def setup_driver(self):
        chrome_options = Options()
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

        try:
            service = Service(self.chromedriver_path)
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
        except WebDriverException as exc:
            print(f"Local ChromeDriver failed, retrying with Selenium Manager: {exc.msg}")
            self.driver = webdriver.Chrome(options=chrome_options)

        stealth(
            self.driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
        )

    def is_video_url(self, url):
        if not url or "douyinstatic.com" in url:
            return False
        return "douyinvod.com" in url or "/video/tos" in url

    def find_video_url(self, timeout_seconds=45):
        WebDriverWait(self.driver, 30).until(
            lambda driver: driver.execute_script("return document.readyState") == "complete"
        )

        deadline = time.time() + timeout_seconds
        seen_urls = set()
        while time.time() < deadline:
            time.sleep(1)
            try:
                logs = self.driver.get_log("performance")
            except Exception:
                logs = []

            for log in logs:
                try:
                    log_json = json.loads(log["message"])["message"]
                    method = log_json.get("method")
                    if method not in ["Network.requestWillBeSent", "Network.responseReceived"]:
                        continue

                    data = log_json["params"]
                    request_or_response = data.get("request", data.get("response", {}))
                    url = request_or_response.get("url", "")
                    if not url or url in seen_urls:
                        continue
                    seen_urls.add(url)

                    if self.is_video_url(url):
                        return url
                except Exception:
                    continue

            try:
                self.driver.execute_script("window.scrollBy(0, 300);")
            except Exception:
                pass

        return None

    def write_header(self):
        video_url = self.find_video_url()

        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.file_path, "w", encoding="utf-8") as file:
            if video_url:
                file.write(f"{video_url}\n")

        if not video_url:
            current_url = self.driver.current_url
            title = self.driver.title
            raise RuntimeError(
                "Could not find a Douyin video stream URL. "
                f"Page title: {title!r}. Current URL: {current_url!r}. "
                "The link may be invalid/private, Douyin may require login/captcha, "
                "or the page did not expose a video request in time."
            )

        print(f"Video URL saved to: {self.file_path}")

    def run(self):
        self.setup_driver()
        try:
            self.driver.get(self.video_url)
            self.write_header()
        finally:
            self.driver.quit()
