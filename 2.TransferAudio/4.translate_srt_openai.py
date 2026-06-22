import argparse
import importlib.util
import json
import os
import time
from pathlib import Path

import pysrt
import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "2.TransferAudio" / "srt" / "output.srt"
DEFAULT_OUTPUT = PROJECT_ROOT / "2.TransferAudio" / "srt" / "output_vi.srt"


def load_project_config():
    config_path = PROJECT_ROOT / "main.py"
    spec = importlib.util.spec_from_file_location("project_main_config", config_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load config file: {config_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def srt_time_to_seconds(time_value):
    return (
        time_value.hours * 3600
        + time_value.minutes * 60
        + time_value.seconds
        + time_value.milliseconds / 1000
    )


def word_count(text):
    return len([word for word in text.replace("\n", " ").split(" ") if word.strip()])


def timing_payload(sub, words_per_minute, tolerance_words):
    duration = srt_time_to_seconds(sub.end) - srt_time_to_seconds(sub.start)
    target_words = max(1, round(duration / 60 * words_per_minute))
    tolerance = max(tolerance_words, round(target_words * 0.15))
    return {
        "id": sub.index,
        "start": str(sub.start),
        "end": str(sub.end),
        "duration_seconds": round(duration, 3),
        "target_words": target_words,
        "min_words": max(1, target_words - tolerance),
        "max_words": target_words + tolerance,
        "source_text": sub.text.replace("\n", " ").strip(),
    }


def build_system_prompt(style):
    return f"""
Ban la bien tap vien long tieng Viet cho video review/ke chuyen ngan.
Nhiem vu: dich phu de tieng Trung sang tieng Viet, giu dung nghia tong the,
nhung phai viet lai de doc vua khoang nghi cua tung subtitle.

Quy tac bat buoc:
- Chi tra ve JSON hop le, khong markdown.
- Giu nguyen id cua tung cau.
- Moi cau dich phai la tieng Viet tu nhien, van phong: {style}.
- Khong them thong tin moi lam sai nghia, nhung duoc rut gon/keo dai cau de vua toc do doc.
- So trong loi thoai phai viet bang chu tieng Viet neu nghe tu nhien.
- Ten rieng nuoc ngoai phai Viet hoa/de doc theo tieng Viet va dung nhat quan.
- Do dai cau dich phai nam trong min_words va max_words.
- Neu cau goc qua ngan, co the them tu noi/dien dat tu nhien ma khong doi nghia.
- Neu cau goc qua dai, uu tien giu y chinh va sac thai, bo chi tiet phu.

Output JSON schema:
{{
  "segments": [
    {{"id": 1, "text": "cau tieng Viet"}}
  ]
}}
""".strip()


def build_user_prompt(items):
    return json.dumps(
        {
            "instruction": "Dich va bien tap cac subtitle sau de vua toc do doc tieng Viet trong cung timeline.",
            "segments": items,
        },
        ensure_ascii=False,
    )


def call_openai_chat(api_key, model, system_prompt, user_prompt, retries, timeout):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "response_format": {"type": "json_object"},
    }

    for attempt in range(retries + 1):
        response = requests.post(url, headers=headers, json=payload, timeout=timeout)
        if response.status_code < 500 and response.status_code != 429:
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            return json.loads(content)

        if attempt == retries:
            response.raise_for_status()
        time.sleep(2 ** attempt)

    raise RuntimeError("OpenAI API request failed after retries")


def translate_batch(api_key, model, system_prompt, items, retries, timeout):
    result = call_openai_chat(
        api_key=api_key,
        model=model,
        system_prompt=system_prompt,
        user_prompt=build_user_prompt(items),
        retries=retries,
        timeout=timeout,
    )
    translated = result.get("segments", [])
    return {int(item["id"]): item["text"].strip() for item in translated}


def find_bad_lengths(items_by_id, translations):
    bad = []
    for item_id, item in items_by_id.items():
        text = translations.get(item_id, "")
        count = word_count(text)
        if count < item["min_words"] or count > item["max_words"]:
            fixed_item = dict(item)
            fixed_item["current_text"] = text
            fixed_item["current_words"] = count
            bad.append(fixed_item)
    return bad


def write_srt(subs, translations, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    for sub in subs:
        if sub.index in translations:
            sub.text = translations[sub.index]
    subs.save(str(output_path), encoding="utf-8")


def write_report(items_by_id, translations, report_path):
    lines = []
    for item_id, item in items_by_id.items():
        text = translations.get(item_id, "")
        count = word_count(text)
        status = "OK" if item["min_words"] <= count <= item["max_words"] else "LECH"
        lines.append(
            f"Cau {item_id}: {status} - {count} tu "
            f"(muc tieu {item['target_words']}, cho phep {item['min_words']}-{item['max_words']})"
        )
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main():
    config = load_project_config()
    parser = argparse.ArgumentParser(
        description="Translate Chinese SRT to Vietnamese with timeline-aware word counts."
    )
    parser.add_argument("--input", default=str(getattr(config, "SOURCE_SRT_PATH", DEFAULT_INPUT)), help="Input Chinese SRT path.")
    parser.add_argument("--output", default=str(getattr(config, "VIETNAMESE_SRT_PATH", DEFAULT_OUTPUT)), help="Output Vietnamese SRT path.")
    parser.add_argument("--model", default=os.getenv("OPENAI_MODEL", getattr(config, "OPENAI_MODEL", "gpt-4o-mini")))
    parser.add_argument("--wpm", type=int, default=getattr(config, "TRANSLATE_WORDS_PER_MINUTE", 190), help="Vietnamese reading speed in words per minute.")
    parser.add_argument("--batch-size", type=int, default=getattr(config, "TRANSLATE_BATCH_SIZE", 12))
    parser.add_argument("--review-passes", type=int, default=getattr(config, "TRANSLATE_REVIEW_PASSES", 2))
    parser.add_argument("--tolerance-words", type=int, default=getattr(config, "TRANSLATE_TOLERANCE_WORDS", 2))
    parser.add_argument("--style", default=getattr(config, "TRANSLATE_STYLE", "Gen Z, cuon, gon, hop review phim/video ngan"))
    parser.add_argument("--timeout", type=int, default=getattr(config, "TRANSLATE_TIMEOUT_SECONDS", 120))
    parser.add_argument("--retries", type=int, default=getattr(config, "TRANSLATE_RETRIES", 3))
    args = parser.parse_args()

    api_key = getattr(config, "OPENAI_API_KEY", "") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY. Put it in main.py or set the OPENAI_API_KEY environment variable.")

    input_path = Path(args.input)
    output_path = Path(args.output)
    report_path = output_path.with_suffix(".report.txt")

    subs = pysrt.open(str(input_path), encoding="utf-8")
    items = [timing_payload(sub, args.wpm, args.tolerance_words) for sub in subs]
    items_by_id = {item["id"]: item for item in items}
    translations = {}
    system_prompt = build_system_prompt(args.style)

    for start in range(0, len(items), args.batch_size):
        batch = items[start:start + args.batch_size]
        print(f"Translating {start + 1}-{start + len(batch)} / {len(items)}")
        translations.update(
            translate_batch(
                api_key=api_key,
                model=args.model,
                system_prompt=system_prompt,
                items=batch,
                retries=args.retries,
                timeout=args.timeout,
            )
        )

    for review_pass in range(1, args.review_passes + 1):
        bad_items = find_bad_lengths(items_by_id, translations)
        if not bad_items:
            break

        print(f"Review pass {review_pass}: fixing {len(bad_items)} timing mismatches")
        for start in range(0, len(bad_items), args.batch_size):
            batch = bad_items[start:start + args.batch_size]
            translations.update(
                translate_batch(
                    api_key=api_key,
                    model=args.model,
                    system_prompt=system_prompt,
                    items=batch,
                    retries=args.retries,
                    timeout=args.timeout,
                )
            )

    write_srt(subs, translations, output_path)
    write_report(items_by_id, translations, report_path)

    remaining_bad = find_bad_lengths(items_by_id, translations)
    print(f"Saved Vietnamese SRT: {output_path}")
    print(f"Saved timing report: {report_path}")
    if remaining_bad:
        print(f"Warning: {len(remaining_bad)} segments still outside target word range.")
    else:
        print("All segments are inside the target word range.")


if __name__ == "__main__":
    main()
