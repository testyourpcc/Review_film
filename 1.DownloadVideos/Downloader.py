import json
import os
import time
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
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
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        if os.getenv("HEADLESS", "0") == "1":
            chrome_options.add_argument("--headless=new")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
        # Do not let driver.get() block until every Douyin resource finishes.
        # find_media_urls() owns the 30-second readiness deadline instead.
        chrome_options.page_load_strategy = "none"

        chrome_binary = os.getenv("CHROME_BIN")
        if chrome_binary:
            chrome_options.binary_location = chrome_binary

        try:
            # Selenium Manager keeps the driver aligned with the installed Chrome.
            self.driver = webdriver.Chrome(options=chrome_options)
        except WebDriverException as exc:
            print(f"Selenium Manager failed, retrying with local ChromeDriver: {exc.msg}")
            service = Service(self.chromedriver_path)
            self.driver = webdriver.Chrome(service=service, options=chrome_options)

        self.driver.set_page_load_timeout(30)

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
        if not url or "douyinstatic.com" in url or self.is_audio_url(url):
            return False
        url_lower = url.lower()
        return (
            "media-video" in url_lower
            or "mime_type=video" in url_lower
            or "douyinvod.com" in url_lower
            or "/video/tos" in url_lower
        )

    def is_audio_url(self, url):
        if not url or "douyinstatic.com" in url:
            return False
        url_lower = url.lower()
        return (
            "media-audio" in url_lower
            or "mime_type=audio" in url_lower
            or "/audio/tos" in url_lower
            or "/audio/" in url_lower and "mp4a" in url_lower
        )

    def find_media_urls(self, timeout_seconds=45, grace_seconds=10):
        try:
            WebDriverWait(self.driver, 30).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
        except TimeoutException:
            print("Page did not finish loading after 30 seconds; scanning captured network requests anyway.")

        deadline = time.time() + timeout_seconds
        seen_urls = set()
        video_url = None
        audio_url = None
        video_found_at = None
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

                    if self.is_audio_url(url):
                        audio_url = audio_url or url
                    elif self.is_video_url(url):
                        if video_url is None:
                            video_url = url
                            video_found_at = time.time()
                except Exception:
                    continue

            if video_url and audio_url:
                return video_url, audio_url

            # A normal MP4 may already contain audio. Give the page a short
            # window to expose a separate DASH audio request before returning.
            if video_url and video_found_at and time.time() - video_found_at >= grace_seconds:
                return video_url, audio_url

            try:
                self.driver.execute_script("window.scrollBy(0, 300);")
            except Exception:
                pass

        return video_url, audio_url

    def write_header(self):
        video_url, audio_url = self.find_media_urls()

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
        if audio_url:
            print("Separate Douyin audio stream detected.")
        return video_url, audio_url

    def run(self):
        self.setup_driver()
        try:
            try:
                self.driver.get(self.video_url)
            except TimeoutException:
                print("Navigation exceeded 30 seconds; using captured network requests.")
            return self.write_header()
        finally:
            self.driver.quit()
