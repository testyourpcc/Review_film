import argparse
import importlib.util
import json
import os
import re
import time
from pathlib import Path

import pysrt
import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "2.TransferAudio" / "srt" / "output.srt"
DEFAULT_OUTPUT = PROJECT_ROOT / "2.TransferAudio" / "srt" / "output_vi.srt"
CJK_PATTERN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")


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


def timing_payload(sub, words_per_minute, max_words_per_minute, tolerance_words):
    duration = srt_time_to_seconds(sub.end) - srt_time_to_seconds(sub.start)

    # Keep target speed below the hard limit. If config is wrong, fix it here
    # instead of producing impossible instructions for the model.
    effective_wpm = min(words_per_minute, max_words_per_minute)
    target_words = max(1, round(duration / 60 * effective_wpm))
    max_words = max(1, round(duration / 60 * max_words_per_minute))

    # Preferred lower bound: helps avoid subtitles that are too short for long
    # timeline slots, but still allows short natural lines when the source is short.
    min_words = max(1, round(target_words * 0.65))

    return {
        "id": sub.index,
        "start": str(sub.start),
        "end": str(sub.end),
        "duration_seconds": round(duration, 3),
        "target_words": target_words,
        "min_words": min_words,
        "max_words": max(target_words, max_words),
        "source_text": sub.text.replace("\n", " ").strip(),
    }


def build_system_prompt(style):
    return f"""
Ban la bien tap vien long tieng chuyen nghiep cho nhieu loai video: review phim,
ke chuyen, vlog, podcast, tin tuc, the thao, giao duc, quang cao, documentary,
short video/TikTok/Douyin. Ban khong dich tung cau may moc. Ban phai hieu
toan bo ngu canh va viet lai thanh loi noi tieng Viet tu nhien, de nghe, khop timeline.

Quy tac bat buoc:
- Chi tra ve JSON hop le, khong markdown.
- Giu nguyen id cua tung segment.
- Moi source_text khong rong phai co text dich khong rong.
- Moi segment phai la tieng Viet tu nhien, phong cach: {style}.
- Noi dung moi segment phai noi logic voi segment truoc va sau.
- Khong dich sat tung chu/cau truc tieng Trung/ngoai ngu. Viet lai nhu nguoi Viet dang noi that.
- Khong them thong tin, bai hoc, dao ly, ket luan, cam xuc hoac tinh tiet khong co trong ban goc.
- Duoc rut gon de khop timeline nhung khong duoc cat mat y chinh, quan he nhan qua, hanh dong quan trong.
- Neu mot cau bi cat qua nhieu subtitle, phai ghep nghia trong dau truoc roi chia lai theo id; khong dich tung manh cau rieng le.
- Doc story_context, context_before va context_after de giu mach lien tuc.

Phong cach va ngon ngu:
- Tu dong chon van phong theo noi dung video, khong ep moi video thanh review phim/Gen Z.
- Neu video giai tri/review/ke chuyen: co the dung loi noi gan gui, cuon, co nhip.
- Neu video tin tuc/kien thuc/documentary: giu ro rang, de hieu, khong qua lo lang.
- Neu video podcast/phong van: giu chat doi thoai tu nhien.
- Neu video ban hang/quang cao: ngan, ro loi ich, khong phong dai qua muc.
- Tieng long chi dung diem xuyet khi hop ngu canh; khong chen vao moi cau.
- Tranh van dich/trang trong nhu "thuc su xung dang", "trong cuoc song", "dieu nay cho thay" neu nguoi noi khong co sac thai do.
- So trong loi thoai nen viet bang chu tieng Viet neu nghe tu nhien.
- Output text chi dung tieng Viet/chu Latin; khong de sot chu Han trong ten goi hay loi thoai.

Nhan vat, ten goi va xung ho:
- Chon dai tu theo quan he nhan vat/nguoi noi/nguoi nghe: anh, em, toi, minh, chung ta, ho, cau, ban, tao, may...
- Khong mac dinh dung tao/may. Chi dung khi quan he va sac thai ban goc phu hop.
- Neu khong ro quan he, uu tien cach noi trung tinh, an toan.
- Ten rieng, danh xung va thuat ngu phai thong nhat trong toan bo video.
- Danh xung kieu "X ca" phai Viet hoa tu nhien va nhat quan, khong dich may moc.
- Cach xung ho trong cung mot cuoc tro chuyen phai dong nhat.

Toi uu theo timeline/TTS:
- Moi segment co duration_seconds, target_words, min_words va max_words.
- target_words la do dai mong muon de TTS doc vua timeline.
- min_words la muc toi thieu nen dat neu source_text co du noi dung.
- max_words la tran tuyet doi, khong duoc vuot.
- Phai viet gan target_words nhat co the nhung van tu nhien.
- Neu duration ngan, viet rat ngan, uu tien y chinh.
- Neu duration dai, viet day du hon de tranh khoang lang/noi qua cham, nhung khong them thong tin ngoai ban goc.
- Khong de cau qua ngan so voi duration neu ban goc co du noi dung.
- Khong de cau qua dai so voi duration vi TTS se bi noi nhanh.
- Neu source_text ngan that su, cau ngan tu nhien duoc chap nhan, khong chen filler de lap day.
- Neu source_text qua dai, uu tien giu y chinh, sac thai, ten goi, hanh dong va ket qua; bo chi tiet phu.

Kiem tra truoc khi tra ket qua:
- Tat ca id trong input deu phai co trong output.
- Khong co text rong neu source_text khong rong.
- Khong co chu Han.
- Khong co segment vuot max_words.
- Neu co the, moi segment nam gan target_words de khop timeline.

Output JSON schema:
{{
  "segments": [
    {{"id": 1, "text": "cau tieng Viet"}}
  ]
}}
""".strip()


def build_story_system_prompt(style):
    return f"""
Ban la bien tap vien kich ban truoc khi long tieng video.
Doc TOAN BO transcript theo dung thu tu, suy luan noi dung va tao story bible bang tieng Viet.
Khong dich chi tiet tung subtitle o buoc nay.

Can xac dinh:
- The loai video: review phim, ke chuyen, vlog, podcast, tin tuc, the thao, giao duc, quang cao, documentary, hoac loai khac.
- Tom tat noi dung theo thu tu mo dau, dien bien, cao trao/diem chinh, ket thuc.
- Danh sach nhan vat/thuc the, vai tro, quan he va moi cach goi xuat hien trong ban goc.
- Moi source_name chi duoc thuoc mot nhan vat. Khong duoc gop hai danh xung cua hai nguoi/nhan vat khac nhau.
- Ghi ro ai dang noi voi ai o nhung doan doi thoai de tranh dao nguoc chu-the.
- Bang cach xung ho tieng Viet nhat quan cho tung cap nhan vat.
- Ten rieng va thuat ngu can dung nhat quan.
- Tat ca vietnamese_name va gia tri vietnamese trong glossary phai viet bang chu Quoc ngu; khong giu chu Han.
- Giong ke va phong cach muc tieu: {style}.
- Cac diem mo ho hoac cau phai dua vao ngu canh moi hieu dung.

Chi tra ve JSON hop le theo schema:
{{
  "video_type": "the loai video",
  "summary": "tom tat toan bo noi dung",
  "plot_beats": ["dien bien/diem chinh 1", "dien bien/diem chinh 2"],
  "characters": [
    {{"source_names": ["ten/cach goi goc"], "vietnamese_name": "ten thong nhat", "role": "vai tro", "relationships": "quan he", "speech_style": "cach xung ho"}}
  ],
  "glossary": [{{"source": "tu goc", "vietnamese": "cach dung thong nhat"}}],
  "narration_rules": ["quy tac can giu"],
  "speaker_notes": [{{"segment_ids": [1, 2], "speaker": "nhan vat", "listener": "nhan vat", "continuity": "y noi tiep"}}]
}}
""".strip()


def analyze_story(api_key, model, items, style, retries, timeout):
    transcript = [
        {"id": item["id"], "source_text": item["source_text"]}
        for item in items
        if item["source_text"]
    ]
    return call_openai_chat(
        api_key=api_key,
        model=model,
        system_prompt=build_story_system_prompt(style),
        user_prompt=json.dumps(
            {
                "instruction": "Phan tich toan bo transcript va tao story bible truoc khi viet ban dich toan cuc.",
                "transcript": transcript,
            },
            ensure_ascii=False,
        ),
        retries=retries,
        timeout=timeout,
    )


def story_context_issues(story_context):
    owners = {}
    issues = []
    for index, character in enumerate(story_context.get("characters", []), start=1):
        label = character.get("vietnamese_name") or f"character_{index}"
        if CJK_PATTERN.search(str(label)):
            issues.append(f"Vietnamese character name {label!r} still contains Chinese characters")
        for source_name in character.get("source_names", []):
            normalized = str(source_name).strip().casefold()
            if not normalized:
                continue
            previous = owners.get(normalized)
            if previous and previous != label:
                issues.append(
                    f"source name {source_name!r} is assigned to both {previous!r} and {label!r}"
                )
            owners[normalized] = label
    for entry in story_context.get("glossary", []):
        vietnamese = str(entry.get("vietnamese", ""))
        if CJK_PATTERN.search(vietnamese):
            issues.append(f"Vietnamese glossary value {vietnamese!r} still contains Chinese characters")
    return issues


def repair_story_context(api_key, model, items, style, story_context, issues, retries, timeout):
    transcript = [
        {"id": item["id"], "source_text": item["source_text"]}
        for item in items
        if item["source_text"]
    ]
    return call_openai_chat(
        api_key=api_key,
        model=model,
        system_prompt=build_story_system_prompt(style),
        user_prompt=json.dumps(
            {
                "instruction": (
                    "Sua story bible dua tren transcript. Tach dung nhan vat, speaker/listener, "
                    "danh xung va quan he; khong bao chua cho ban cu. Tra lai TOAN BO JSON story bible."
                ),
                "detected_issues": issues,
                "current_story_context": story_context,
                "transcript": transcript,
            },
            ensure_ascii=False,
        ),
        retries=retries,
        timeout=timeout,
    )


def compact_item(item):
    return {"id": item["id"], "source_text": item["source_text"]}


def build_batch_context(items, translations, start, end, context_segments):
    before = items[max(0, start - context_segments):start]
    after = items[end:min(len(items), end + context_segments)]
    neighbor_ids = {item["id"] for item in before + after}
    translated_neighbors = [
        {"id": item_id, "text": translations[item_id]}
        for item_id in sorted(neighbor_ids)
        if item_id in translations
    ]
    return {
        "context_before": [compact_item(item) for item in before],
        "context_after": [compact_item(item) for item in after],
        "existing_neighbor_translations": translated_neighbors,
    }


def build_review_context(items_by_id, translations, batch, context_segments):
    target_ids = {item["id"] for item in batch}
    neighbor_ids = set()
    for item_id in target_ids:
        neighbor_ids.update(range(item_id - context_segments, item_id + context_segments + 1))
    neighbor_ids.difference_update(target_ids)
    source_neighbors = [
        compact_item(items_by_id[item_id])
        for item_id in sorted(neighbor_ids)
        if item_id in items_by_id
    ]
    translated_neighbors = [
        {"id": item_id, "text": translations[item_id]}
        for item_id in sorted(neighbor_ids)
        if item_id in translations
    ]
    return {
        "nearby_source_segments": source_neighbors,
        "existing_neighbor_translations": translated_neighbors,
    }


def build_user_prompt(items, story_context, batch_context=None, instruction=None):
    return json.dumps(
        {
            "instruction": instruction or "Dich va bien tap TOAN BO transcript thanh mot kich ban tieng Viet lien mach, dong thoi giu moi cau vua timeline.",
            "story_context": story_context,
            **(batch_context or {}),
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


def translate_batch(api_key, model, system_prompt, items, story_context, batch_context=None, retries=3, timeout=120, instruction=None):
    result = call_openai_chat(
        api_key=api_key,
        model=model,
        system_prompt=system_prompt,
        user_prompt=build_user_prompt(items, story_context, batch_context, instruction),
        retries=retries,
        timeout=timeout,
    )
    translated = result.get("segments", [])
    return {int(item["id"]): item["text"].strip() for item in translated}


def find_incomplete_ids(items, translations):
    return [
        item["id"]
        for item in items
        if item["source_text"] and not translations.get(item["id"], "").strip()
    ]


def usable_subtitles(subs):
    cleaned = pysrt.SubRipFile()
    dropped_ids = []
    for sub in subs:
        duration = srt_time_to_seconds(sub.end) - srt_time_to_seconds(sub.start)
        if not sub.text.replace("\n", " ").strip() or duration <= 0:
            dropped_ids.append(sub.index)
            continue
        cleaned.append(sub)
    return cleaned, dropped_ids


def find_bad_lengths(items_by_id, translations):
    bad = []
    for item_id, item in items_by_id.items():
        text = translations.get(item_id, "")
        count = word_count(text)
        if not text.strip() or count > item["max_words"] or CJK_PATTERN.search(text):
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
        if not text.strip():
            status = "TRONG"
        elif count > item["max_words"]:
            status = "QUA_DAI"
        else:
            status = "OK"
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
    parser.add_argument("--wpm", type=int, default=getattr(config, "TRANSLATE_WORDS_PER_MINUTE", 145), help="Target Vietnamese reading speed in words per minute.")
    parser.add_argument("--max-wpm", type=int, default=getattr(config, "TRANSLATE_MAX_WORDS_PER_MINUTE", 170), help="Hard maximum reading speed; overlong segments are rejected before TTS.")
    parser.add_argument("--batch-size", type=int, default=getattr(config, "TRANSLATE_BATCH_SIZE", 12))
    parser.add_argument("--context-segments", type=int, default=getattr(config, "TRANSLATE_CONTEXT_SEGMENTS", 3))
    parser.add_argument("--review-passes", type=int, default=getattr(config, "TRANSLATE_REVIEW_PASSES", 2))
    parser.add_argument("--tolerance-words", type=int, default=getattr(config, "TRANSLATE_TOLERANCE_WORDS", 2))
    parser.add_argument("--style", default=getattr(config, "TRANSLATE_STYLE", "Tu nhien, de nghe, khop timeline, phu hop ngu canh video"))
    parser.add_argument("--timeout", type=int, default=getattr(config, "TRANSLATE_TIMEOUT_SECONDS", 120))
    parser.add_argument("--retries", type=int, default=getattr(config, "TRANSLATE_RETRIES", 3))
    args = parser.parse_args()

    api_key = getattr(config, "OPENAI_API_KEY", "") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY. Put it in main.py or set the OPENAI_API_KEY environment variable.")

    input_path = Path(args.input)
    output_path = Path(args.output)
    report_path = output_path.with_suffix(".report.txt")
    context_path = output_path.with_suffix(".context.json")

    subs = pysrt.open(str(input_path), encoding="utf-8")
    subs, dropped_ids = usable_subtitles(subs)
    if dropped_ids:
        print(f"Dropped empty/zero-duration source subtitles: {dropped_ids}")
    items = [timing_payload(sub, args.wpm, args.max_wpm, args.tolerance_words) for sub in subs]
    items_by_id = {item["id"]: item for item in items}
    translations = {}
    system_prompt = build_system_prompt(args.style)

    print(f"Analyzing full story context from {len(items)} subtitle segments...")
    story_context = analyze_story(
        api_key=api_key,
        model=args.model,
        items=items,
        style=args.style,
        retries=args.retries,
        timeout=args.timeout,
    )
    context_issues = story_context_issues(story_context)
    if context_issues:
        print(f"Story context validation found {len(context_issues)} issue(s); repairing...")
        story_context = repair_story_context(
            api_key=api_key,
            model=args.model,
            items=items,
            style=args.style,
            story_context=story_context,
            issues=context_issues,
            retries=args.retries,
            timeout=args.timeout,
        )
        remaining_context_issues = story_context_issues(story_context)
        if remaining_context_issues:
            raise RuntimeError(f"Story context is still inconsistent: {remaining_context_issues}")
    context_path.parent.mkdir(parents=True, exist_ok=True)
    context_path.write_text(json.dumps(story_context, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved story context: {context_path}")

    print(f"Translating all {len(items)} segments as one continuous screenplay...")
    translations = translate_batch(
        api_key=api_key,
        model=args.model,
        system_prompt=system_prompt,
        items=items,
        story_context=story_context,
        retries=args.retries,
        timeout=args.timeout,
        instruction=(
            "Dich TOAN BO transcript trong mot lan nhu mot kich ban long tieng duy nhat. "
            "Moi segment phai khop timeline dua tren duration_seconds, min_words, target_words va max_words. "
            "Viet gan target_words nhat co the, khong qua ngan neu source_text co du noi dung, va tuyet doi khong vuot max_words. "
            "Neu duration ngan thi rut gon manh, neu duration dai thi viet day du hon nhung khong them thong tin ngoai ban goc. "
            "Tu dong chon giong van phu hop voi the loai video trong story_context; khong ep moi video thanh review phim/Gen Z. "
            "Uu tien mach noi dung, quan he nhan qua, cach xung ho va ten goi nhat quan. "
            "Viet nhu loi noi tieng Viet tu nhien, de nghe, khong mang mui ban dich. "
            "Moi cau phai dan tu nhien sang cau tiep theo. Khong tu them loi tong ket, dao ly hay cam xuc khong co trong ban goc. "
            "Giu dung id va tra ve day du tat ca id."
        ),
    )

    for review_pass in range(1, args.review_passes + 1):
        bad_items = find_bad_lengths(items_by_id, translations)
        if not bad_items:
            break

        print(f"Timing pass {review_pass}: shortening {len(bad_items)} overlong/empty segments")
        for start in range(0, len(bad_items), args.batch_size):
            batch = bad_items[start:start + args.batch_size]
            batch_context = build_review_context(
                items_by_id=items_by_id,
                translations=translations,
                batch=batch,
                context_segments=args.context_segments,
            )
            reviewed = translate_batch(
                api_key=api_key,
                model=args.model,
                system_prompt=system_prompt,
                items=batch,
                story_context=story_context,
                batch_context=batch_context,
                retries=args.retries,
                timeout=args.timeout,
                instruction=(
                    "Chi sua cac segment nay vi dang rong, qua ngan so voi timeline, vuot max_words hoac con chu Han. "
                    "Neu con chu Han thi bat buoc doi sang ten/cach goi tieng Viet bang chu Quoc ngu. "
                    "Can lai do dai theo min_words, target_words va max_words: gan target_words nhat co the, tuyet doi khong vuot max_words. "
                    "Neu cau qua dai thi rut gon de khong doc nhanh; neu cau qua ngan ma source_text co du y thi bo sung dung y goc de tranh noi cham/khoang lang. "
                    "Khong them thong tin ngoai ban goc, khong viet filler. "
                    "Giu nguyen y, cam xuc, ten goi, cach xung ho va mach noi cua ban dich toan cuc. Khong viet lai cac cau lan can."
                ),
            )
            translations.update(reviewed)

    incomplete_ids = find_incomplete_ids(items, translations)
    if incomplete_ids:
        raise RuntimeError(f"Translation returned empty text for source segments: {incomplete_ids}")
    cjk_ids = [item_id for item_id, text in translations.items() if CJK_PATTERN.search(text)]
    if cjk_ids:
        raise RuntimeError(f"Vietnamese translation still contains Chinese characters: {cjk_ids}")

    write_srt(subs, translations, output_path)
    write_report(items_by_id, translations, report_path)

    remaining_bad = find_bad_lengths(items_by_id, translations)
    print(f"Saved Vietnamese SRT: {output_path}")
    print(f"Saved timing report: {report_path}")
    if remaining_bad:
        bad_ids = [item["id"] for item in remaining_bad]
        print(
            f"Warning: segments {bad_ids} still exceed the preferred limit of "
            f"{args.max_wpm} words/minute; TTS will fit them to their timeline."
        )
    else:
        print("All segments contain text and stay below the maximum reading speed.")


if __name__ == "__main__":
    main()
