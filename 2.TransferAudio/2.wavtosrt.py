import whisper
import math

def convert_wav_to_srt(wav_file, output_srt_path, target_segments=50):
    # Load Whisper model (adjust size as needed)
    model = whisper.load_model("large")  # or "large"

    # Transcribe with word timestamps
    result = model.transcribe(wav_file, word_timestamps=True)
    segments = result["segments"]

    # If segments already <= target, write directly
    if len(segments) <= target_segments:
        merged = segments
    else:
        # Compute batch size: number of original segments to merge per target segment
        batch_size = math.ceil(len(segments) / target_segments)
        merged = []
        for i in range(0, len(segments), batch_size):
            batch = segments[i:i+batch_size]
            # Merge text and time
            start_time = batch[0]['start']
            end_time = batch[-1]['end']
            text = ' '.join([seg['text'].strip() for seg in batch])
            merged.append({'start': start_time, 'end': end_time, 'text': text})

    # Compose SRT content
    srt_lines = []
    for idx, seg in enumerate(merged, start=1):
        # Format timestamp
        def fmt(ts):
            h = int(ts // 3600)
            m = int((ts % 3600) // 60)
            s = int(ts % 60)
            ms = int((ts - int(ts)) * 1000)
            return f"{h:02}:{m:02}:{s:02},{ms:03}"

        srt_lines.append(f"{idx}")
        srt_lines.append(f"{fmt(seg['start'])} --> {fmt(seg['end'])}")
        srt_lines.append(seg['text'])
        srt_lines.append("")  # blank line

    # Write file
    with open(output_srt_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(srt_lines))
    print(f"Generated SRT with {len(merged)} segments at: {output_srt_path}")


if __name__ == '__main__':
    wav = r'C:\Users\ngodu\Desktop\Videos\2.TransferAudio\outputwav\output.wav'
    out_srt = r'C:\Users\ngodu\Desktop\Videos\2.TransferAudio\srt\output.srt'
    convert_wav_to_srt(wav, out_srt, target_segments=50)
