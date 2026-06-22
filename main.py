import argparse
import importlib
import os
import json
import shutil
import subprocess
import sys
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent
DOWNLOAD_DIR = PROJECT_ROOT / "1.DownloadVideos"
TRANSFER_DIR = PROJECT_ROOT / "2.TransferAudio"
MERGE_DIR = PROJECT_ROOT / "3.Merge"
FINAL_DIR = PROJECT_ROOT / "4.Final"
DRIVER_DIR = PROJECT_ROOT / "driver"

# Download step
DOUYIN_URLS_FILE = DOWNLOAD_DIR / "videourls.txt"
REAL_VIDEO_URLS_FILE = DOWNLOAD_DIR / "output_link_video.txt"
CHROMEDRIVER_PATH = DRIVER_DIR / "chromedriver.exe"
DOWNLOADED_VIDEO_PATH = DOWNLOAD_DIR / "output" / "1.mp4"

# Audio/subtitle step
OUTPUT_WAV_PATH = TRANSFER_DIR / "outputwav" / "output.wav"
VIDEO_NO_SOUND_PATH = TRANSFER_DIR / "videonosounds" / "videonosounds.mp4"
SOURCE_SRT_PATH = TRANSFER_DIR / "srt" / "output.srt"
VIETNAMESE_SRT_PATH = TRANSFER_DIR / "srt" / "output_vi.srt"
VIETNAMESE_AUDIO_PATH = TRANSFER_DIR / "ouputsounds" / "output.mp3"
MIN_VIDEO_DURATION_SECONDS = 5

# OpenAI translation step
# Set OPENAI_API_KEY in your shell before running, or paste it locally here.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = "gpt-4o-mini"
TRANSCRIBE_PROVIDER = os.getenv("TRANSCRIBE_PROVIDER", "openai")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "medium")
OPENAI_TRANSCRIBE_MODEL = os.getenv("OPENAI_TRANSCRIBE_MODEL", "whisper-1")
TRANSLATE_WORDS_PER_MINUTE = 190
TRANSLATE_BATCH_SIZE = 12
TRANSLATE_REVIEW_PASSES = 2
TRANSLATE_TOLERANCE_WORDS = 2
TRANSLATE_TIMEOUT_SECONDS = 120
TRANSLATE_RETRIES = 3
TRANSLATE_STYLE = "Gen Z, cuon, gon, hop review phim/video ngan"

# Final merge step
FINAL_OUTPUT_DIR = FINAL_DIR
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output"


def run_script(script_path, cwd=None):
    subprocess.run([sys.executable, str(script_path)], check=True, cwd=str(cwd or PROJECT_ROOT))


def run_capture(command):
    return subprocess.run(command, check=True, capture_output=True, text=True)


def remove_path(path):
    path = Path(path)
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def clean_pycache():
    for path in PROJECT_ROOT.rglob("__pycache__"):
        remove_path(path)


def clean_intermediate_files(clean_final_temp=True):
    paths = [
        REAL_VIDEO_URLS_FILE,
        DOWNLOADED_VIDEO_PATH,
        OUTPUT_WAV_PATH,
        VIDEO_NO_SOUND_PATH,
        SOURCE_SRT_PATH,
        VIETNAMESE_SRT_PATH,
        VIETNAMESE_SRT_PATH.with_suffix(".report.txt"),
        VIETNAMESE_AUDIO_PATH,
        PROJECT_ROOT / "alert.txt",
        TRANSFER_DIR / "video_urls.txt",
    ]

    for pattern in ["tmp*.mp3", "adjusted*.mp3", "silence.mp3", "temp_*.mp3", "file_list.txt", "concat_list.txt"]:
        paths.extend(PROJECT_ROOT.glob(pattern))
        paths.extend(TRANSFER_DIR.glob(pattern))

    if clean_final_temp:
        paths.extend(FINAL_DIR.glob("*.mp4"))

    for path in paths:
        remove_path(path)
    clean_pycache()


def read_video_urls(urls_file):
    urls = [
        line.strip()
        for line in Path(urls_file).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not urls:
        raise RuntimeError(f"No video URLs found in {urls_file}")
    return urls


def load_download_modules():
    if str(DOWNLOAD_DIR) not in sys.path:
        sys.path.insert(0, str(DOWNLOAD_DIR))
    downloader_module = importlib.import_module("Downloader")
    videos_module = importlib.import_module("videos")
    return downloader_module.VideoURLExtractor, videos_module.download_video


def extract_real_video_url(douyin_url):
    VideoURLExtractor, _ = load_download_modules()
    remove_path(REAL_VIDEO_URLS_FILE)
    extractor = VideoURLExtractor(video_url=douyin_url, chromedriver_path=CHROMEDRIVER_PATH)
    extractor.run()

    urls = read_video_urls(REAL_VIDEO_URLS_FILE)
    return urls[0]


def download_video(douyin_url):
    _, download_video_func = load_download_modules()
    real_video_url = extract_real_video_url(douyin_url)
    DOWNLOADED_VIDEO_PATH.parent.mkdir(parents=True, exist_ok=True)
    remove_path(DOWNLOADED_VIDEO_PATH)
    download_video_func(real_video_url, str(DOWNLOADED_VIDEO_PATH))
    if not DOWNLOADED_VIDEO_PATH.exists():
        raise RuntimeError(f"Download failed: {DOWNLOADED_VIDEO_PATH}")
    validate_downloaded_video(DOWNLOADED_VIDEO_PATH, real_video_url)


def probe_video(video_path):
    result = run_capture([
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration:stream=codec_type",
        "-of",
        "json",
        str(video_path),
    ])
    return json.loads(result.stdout)


def validate_downloaded_video(video_path, source_url):
    info = probe_video(video_path)
    duration = float(info.get("format", {}).get("duration", 0) or 0)
    streams = info.get("streams", [])
    has_audio = any(stream.get("codec_type") == "audio" for stream in streams)
    has_video = any(stream.get("codec_type") == "video" for stream in streams)

    if not has_video or not has_audio or duration < MIN_VIDEO_DURATION_SECONDS:
        remove_path(video_path)
        raise RuntimeError(
            "Downloaded file does not look like the target Douyin video. "
            f"duration={duration:.2f}s, has_video={has_video}, has_audio={has_audio}. "
            f"source_url={source_url}"
        )


def sanitize_final_video(video_path):
    video_path = Path(video_path)
    temp_path = video_path.with_name(f"{video_path.stem}.clean{video_path.suffix}")
    remove_path(temp_path)

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-map",
            "0:v:0",
            "-map",
            "0:a:0",
            "-c",
            "copy",
            "-map_metadata",
            "-1",
            "-map_chapters",
            "-1",
            "-dn",
            "-sn",
            "-movflags",
            "+faststart",
            str(temp_path),
        ],
        check=True,
    )
    remove_path(video_path)
    shutil.move(str(temp_path), str(video_path))


def translate_srt():
    script_path = TRANSFER_DIR / "4.translate_srt_openai.py"
    run_script(script_path)
    if not VIETNAMESE_SRT_PATH.exists():
        raise RuntimeError(f"Translation failed: {VIETNAMESE_SRT_PATH}")
    shutil.copy2(VIETNAMESE_SRT_PATH, SOURCE_SRT_PATH)


def run_transfer_steps():
    run_script(TRANSFER_DIR / "1.mp4towav.py", cwd=TRANSFER_DIR)
    run_script(TRANSFER_DIR / "2.wavtosrt.py", cwd=TRANSFER_DIR)
    translate_srt()
    run_script(TRANSFER_DIR / "3.srttoaudio.py", cwd=TRANSFER_DIR)


def collect_merged_video(output_dir, output_index):
    output_dir.mkdir(parents=True, exist_ok=True)
    before = set(FINAL_DIR.glob("*.mp4"))
    run_script(MERGE_DIR / "merge.py", cwd=MERGE_DIR)
    after = set(FINAL_DIR.glob("*.mp4"))
    created = sorted(after - before, key=lambda path: path.stat().st_mtime, reverse=True)
    if not created:
        created = sorted(FINAL_DIR.glob("*.mp4"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not created:
        raise RuntimeError("Merge finished but no MP4 output was found.")

    merged_video = created[0]
    final_path = output_dir / f"{output_index}.mp4"
    if final_path.resolve() == merged_video.resolve():
        sanitize_final_video(final_path)
        return final_path

    remove_path(final_path)
    shutil.move(str(merged_video), str(final_path))
    sanitize_final_video(final_path)
    return final_path


def process_one_video(douyin_url, output_dir, output_index):
    print(f"\n=== Video {output_index}: download ===")
    download_video(douyin_url)

    print(f"=== Video {output_index}: audio, srt, translate, tts ===")
    run_transfer_steps()

    print(f"=== Video {output_index}: merge ===")
    final_path = collect_merged_video(output_dir, output_index)
    print(f"Done: {final_path}")
    return final_path


def parse_args():
    parser = argparse.ArgumentParser(description="Run the full Douyin to Vietnamese dubbed video flow.")
    parser.add_argument("-r", "--routes", default=str(DOUYIN_URLS_FILE), help="Text file containing Douyin URLs.")
    parser.add_argument("-o", "--output", default=str(DEFAULT_OUTPUT_DIR), help="Folder for final MP4 outputs.")
    parser.add_argument("--keep-temp", action="store_true", help="Keep intermediate wav/srt/mp3 files.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    output_dir = Path(args.output).resolve()
    clean_final_temp = output_dir != FINAL_DIR.resolve()
    clean_intermediate_files(clean_final_temp=clean_final_temp)

    urls = read_video_urls(args.routes)
    final_outputs = []
    try:
        for index, url in enumerate(urls, start=1):
            final_outputs.append(process_one_video(url, output_dir, index))
            if not args.keep_temp:
                clean_intermediate_files(clean_final_temp=clean_final_temp)
    finally:
        clean_pycache()

    print("\nAll done. Final outputs:")
    for path in final_outputs:
        print(path)
