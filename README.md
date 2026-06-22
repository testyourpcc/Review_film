# Review Film Pipeline

Pipeline tu dong de tai video Douyin, tach audio, tao SRT bang OpenAI transcription API, dich/bien tap SRT sang tieng Viet bang OpenAI API, tao voice TTS tieng Viet, ghep lai video va lam sach metadata dau ra.

Ban nay co the chay theo 2 kieu:

- Local CLI: chay truc tiep tren may.
- API server: goi HTTP API de job chay tren may ao/VM/container.

## Yeu Cau

- Python 3.9+
- ffmpeg va ffprobe trong PATH
- Google Chrome hoac Chromium
- Internet
- OpenAI API key

Khong can GPU neu dung cau hinh mac dinh `TRANSCRIBE_PROVIDER=openai`.

## Cai Dat

```bash
git clone https://github.com/testyourpcc/Review_film.git
cd Review_film
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Set OpenAI API key:

```bash
export OPENAI_API_KEY="sk-..."
```

Windows PowerShell:

```powershell
$env:OPENAI_API_KEY="sk-..."
```

Hoac tao file `.env` tu `.env.example`:

```text
OPENAI_API_KEY=sk-...
PIPELINE_API_KEY=your-long-random-secret
TRANSCRIBE_PROVIDER=openai
OPENAI_TRANSCRIBE_MODEL=whisper-1
```

File `.env` da nam trong `.gitignore`, khong commit len GitHub.

## Chay Local

Tao file URL, moi dong mot link Douyin:

```text
https://v.douyin.com/...
https://v.douyin.com/...
```

Chay full flow:

```bash
python main.py -r videosurl.txt -o output
```

Windows neu dung Python Launcher:

```powershell
py main.py -r .\videosurl.txt -o .\output
```

Output:

```text
output/1.mp4
output/2.mp4
```

Mac dinh pipeline se don file tam sau moi video. Neu muon giu file tam de debug:

```bash
python main.py -r videosurl.txt -o output --keep-temp
```

## Chay Bang API

Set them API key rieng de bao ve endpoint:

```bash
export PIPELINE_API_KEY="your-secret"
export OPENAI_API_KEY="sk-..."
```

Chay server:

```bash
uvicorn server:app --host 0.0.0.0 --port 8000
```

Tao job:

```bash
curl -X POST http://YOUR_VM_IP:8000/run \
  -H "X-API-Key: your-secret" \
  -H "Content-Type: application/json" \
  -d '{"urls":["https://v.douyin.com/..."]}'
```

Xem status:

```bash
curl http://YOUR_VM_IP:8000/jobs/JOB_ID \
  -H "X-API-Key: your-secret"
```

Tai output qua API:

```bash
curl -L http://YOUR_VM_IP:8000/jobs/JOB_ID/files/1.mp4 \
  -H "X-API-Key: your-secret" \
  -o 1.mp4
```

Xem log:

```bash
curl http://YOUR_VM_IP:8000/jobs/JOB_ID/log \
  -H "X-API-Key: your-secret"
```

API hien chay queue tuan tu 1 job/luc de tranh xung dot file tam trong pipeline.
Mac dinh output API nam trong `output/JOB_ID/1.mp4`.

## Chay Bang Docker

Docker image duoc toi uu de chay re tren CPU: mac dinh dung OpenAI `whisper-1` transcription API de lay SRT, khong cai PyTorch/Whisper local va khong can GPU.
Container mac dinh chay Chrome headless (`HEADLESS=1`) de hop App Service/Container Apps/VM.

Build image:

```bash
docker build -t review-film-pipeline .
```

Run API container:

```bash
docker run --rm -p 8000:8000 \
  --env-file .env \
  -v "$(pwd)/output:/app/output" \
  -v "$(pwd)/jobs:/app/jobs" \
  review-film-pipeline
```

Windows PowerShell:

```powershell
docker run --rm -p 8000:8000 `
  --env-file .env `
  -v "D:\Review_film\output:/app/output" `
  -v "D:\Review_film\jobs:/app/jobs" `
  review-film-pipeline
```

Sau do goi API nhu phan `Chay Bang API`.
Voi lenh Windows tren, file hoan thanh se nam tai `D:\Review_film\output\JOB_ID\1.mp4`.

Profile khuyen dung cho App Service/VM CPU:

```text
TRANSCRIBE_PROVIDER=openai
OPENAI_TRANSCRIBE_MODEL=whisper-1
OPENAI_MODEL=gpt-4o-mini
```

Ly do dung `whisper-1`: pipeline can SRT de giu timeline. OpenAI `whisper-1` ho tro output `srt`; cac model transcription moi hon nhu `gpt-4o-transcribe` co do chinh xac cao hon trong docs, nhung khong ho tro output SRT truc tiep tai thoi diem nay. Neu OpenAI cap nhat model moi co ho tro SRT, chi can doi `OPENAI_TRANSCRIBE_MODEL`.

## Deploy Azure App Service Container

Azure App Service ho tro custom Docker image cho Linux App Service. Cach di don gian:

1. Build image.
2. Push len Azure Container Registry.
3. Tao App Service Linux custom container tro toi image do.
4. Set app settings:

```text
OPENAI_API_KEY=YOUR_OPENAI_KEY
PIPELINE_API_KEY=your-secret
TRANSCRIBE_PROVIDER=openai
OPENAI_TRANSCRIBE_MODEL=whisper-1
PORT=8000
WEBSITES_PORT=8000
```

App Service phu hop neu ban uu tien chi phi va dung `TRANSCRIBE_PROVIDER=openai`, vi container nhe hon va khong phu thuoc GPU.

## Cai Dat Tren Azure VM

Ubuntu:

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip ffmpeg chromium-browser
```

Clone repo va cai dependencies nhu phan Cai Dat. Sau do chay API bang `uvicorn`.

Nen cau hinh Azure Network Security Group chi mo port `8000` cho IP cua ban, khong public tran neu khong can.

## Metadata Output

Sau khi merge, pipeline remux file MP4 cuoi voi ffmpeg de lam sach:

- metadata nguon
- chapters
- subtitle stream
- data stream
- tag kieu title/comment/creation time neu co

Output van con metadata ky thuat MP4 binh thuong nhu `major_brand`, `compatible_brands`, `VideoHandler`, `SoundHandler`.

## Cau Hinh Quan Trong

Trong `main.py`:

- `OPENAI_MODEL`
- `TRANSCRIBE_PROVIDER` (`openai` mac dinh; `local` chi dung khi ban tu cai them Whisper)
- `OPENAI_TRANSCRIBE_MODEL`
- `WHISPER_MODEL`
- `TRANSLATE_WORDS_PER_MINUTE`
- `TRANSLATE_BATCH_SIZE`
- `TRANSLATE_REVIEW_PASSES`
- `MIN_VIDEO_DURATION_SECONDS`

Khuyen nghi de secret trong env:

- `OPENAI_API_KEY`
- `PIPELINE_API_KEY`
- `API_OUTPUT_ROOT`
- `JOBS_DIR`

Khong commit API key that len GitHub.

## Ghi Chu

ChromeDriver local trong `driver/` chi la fallback. Neu bi lech version, Selenium Manager se tu detect Chrome va tai driver phu hop.

Tag on dinh dau tien cua ban API + local la:

```text
v1.0-local-api-base
```

Tag Docker CPU/API gon nhe:

```text
v1.2-cost-optimized-docker
```
