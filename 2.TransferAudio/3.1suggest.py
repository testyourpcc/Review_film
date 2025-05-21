# srt_word_suggestion.py
import pysrt

def srt_time_to_seconds(time):
    """Chuyển đổi đối tượng pysrt.SubRipTime → giây (float)."""
    return time.hours * 3600 + time.minutes * 60 + time.seconds + time.milliseconds / 1000

def suggest_words_for_srt(
        srt_file: str,
        target_rate: int = 190,
        alert_path: str = "alert.txt",
        to_console: bool = False,
    ):
    """
    Xuất gợi ý cho từng câu trong SRT theo định dạng:
      - Nếu số từ hiện tại trong khoảng ±2 so với lý tưởng, báo là đã đạt chuẩn (kèm số từ hiện tại).
      - Ngược lại, báo cần chính xác X từ để tối ưu (hiện tại Y từ).
    """
    subs = pysrt.open(srt_file, encoding="utf-8")
    lines = []

    for idx, sub in enumerate(subs, start=1):
        start = srt_time_to_seconds(sub.start)
        end   = srt_time_to_seconds(sub.end)
        dur   = end - start

        # Tính số từ lý tưởng theo tốc độ đọc
        ideal_wc = max(1, round(dur / 60 * target_rate))
        # Đếm số từ hiện tại trong subtitle
        actual_wc = len(sub.text.split())

        # So sánh với sai số cho phép ±2 từ
        if abs(actual_wc - ideal_wc) <= 2:
            lines.append(f"Câu {idx}: đạt chuẩn ({actual_wc} từ)")
        else:
            lines.append(f"Câu {idx}: cần {ideal_wc} từ để tối ưu (hiện tại {actual_wc} từ)")

    output = "\n".join(lines)

    if to_console:
        print(output)
    else:
        with open(alert_path, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"• Đã ghi gợi ý vào {alert_path}")

if __name__ == "__main__":
    # === ĐỔI ĐƯỜNG DẪN CHO PHÙ HỢP ===
    srt_path = r"C:\Users\ngodu\Desktop\Videos\2.TransferAudio\srt\output.srt"
    suggest_words_for_srt(srt_path, target_rate=190)
