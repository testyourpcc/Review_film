import pysrt
from gtts import gTTS
import subprocess
import os
from mutagen.mp3 import MP3

def get_mp3_duration(file_path: str) -> float:
    """
    Trả về thời lượng (giây) của một file MP3.
    """
    audio = MP3(file_path)
    return audio.info.length

def split_atempo(speed: float):
    """Tách tốc độ thành chuỗi filter atempo hợp lệ cho ffmpeg."""
    factors, remain = [], speed
    while remain > 2.0 or remain < 0.5:
        step = 2.0 if remain > 2.0 else 0.5
        factors.append(step)
        remain /= step
    factors.append(remain)
    return ",".join(f"atempo={f:.4f}" for f in factors)

def create_tts_with_speed(text: str, lang: str, speed: float, output_file: str):
    temp_raw = "temp_tts_raw.mp3"

    # Bước 1: Tạo TTS cơ bản
    tts = gTTS(text=text, lang=lang)
    tts.save(temp_raw)

    # Bước 2: Dùng ffmpeg tăng/giảm tốc độ
    atempo_filter = split_atempo(speed)
    subprocess.run([
        "ffmpeg", "-y", "-i", temp_raw,
        "-filter:a", atempo_filter,
        output_file
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Xoá file tạm
    if os.path.exists(temp_raw):
        os.remove(temp_raw)

    return output_file

def add_silence(duration: float, output_file: str):
    """
    Tạo một file MP3 câm với thời lượng tương ứng (giây).
    """
    if duration <= 0:
        raise ValueError("Thời lượng phải lớn hơn 0")

    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
        "-t", str(duration),
        "-q:a", "9",
        output_file
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def merge_mp3(main_file: str, silence_file: str, output_file: str = None):
    """
    Nối file âm thanh chính với file câm bằng ffmpeg, sau đó xoá 2 file tạm.
    """
    if output_file is None:
        output_file = main_file

    concat_list = "concat_list.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        f.write(f"file '{main_file}'\n")
        f.write(f"file '{silence_file}'\n")

    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_list,
        "-acodec", "libmp3lame", "-b:a", "128k",  # Ép tái mã hóa
        output_file
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


    # Xoá file tạm
    if os.path.exists(main_file):
        os.remove(main_file)
    if os.path.exists(silence_file):
        os.remove(silence_file)
    if os.path.exists(concat_list):
        os.remove(concat_list)

def speedup(input_file: str, original_duration: float, target_duration: float, output_file: str = None):
    if output_file is None:
        output_file = input_file

    current_speed = original_duration / target_duration
    atempo_filter = split_atempo(current_speed)

    temp_output = "temp_speedup.mp3"
    subprocess.run([
        "ffmpeg", "-y", "-i", input_file,
        "-filter:a", atempo_filter,
        temp_output
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    os.replace(temp_output, output_file)

total = 0
def adjust(input_path):
    global total
    subs = pysrt.open(input_path, encoding="utf-8")
    for sub in subs:
        print(sub.index, sub.start, sub.end, sub.text)
        duration = (sub.end.ordinal - sub.start.ordinal) / 1000.0
        create_tts_with_speed(sub.text, lang="vi", speed=1.8, output_file=f"tmp{sub.index}.mp3")
        tmp_duration = get_mp3_duration(f"tmp{sub.index}.mp3")
        difference = duration - tmp_duration
        if difference > 0:
            add_silence(difference, "silence.mp3")
            merge_mp3(f"tmp{sub.index}.mp3", "silence.mp3", f"adjusted{sub.index}.mp3")
        elif difference < 0:
            speedup(f"tmp{sub.index}.mp3", tmp_duration, duration, f"adjusted{sub.index}.mp3")
            os.remove(f"tmp{sub.index}.mp3")
        else:
            os.rename(f"tmp{sub.index}.mp3", f"adjusted{sub.index}.mp3")

        total += 1

def merge(total):
    with open("file_list.txt", "w", encoding="utf-8") as f:
        for i in range(1, total + 1):
            f.write(f"file 'adjusted{i}.mp3'\n")

    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "file_list.txt",
        "-acodec", "libmp3lame", "-b:a", "128k", r"C:\Users\ngodu\Desktop\Videos\2.TransferAudio\ouputsounds\output.mp3"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    os.remove("file_list.txt")

    for i in range(1, total + 1):
        if os.path.exists(f"adjusted{i}.mp3"):
            os.remove(f"adjusted{i}.mp3")

if __name__ == "__main__":
    input_path = r"C:\Users\ngodu\Desktop\Videos\2.TransferAudio\srt\output.srt"
    adjust(input_path)
    merge(total)
