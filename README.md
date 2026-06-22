# Review Film Pipeline

Pipeline tu dong de tai video Douyin, tach audio, tao SRT bang Whisper, dich/bien tap SRT sang tieng Viet bang OpenAI API, tao voice TTS tieng Viet, ghep lai video va lam sach metadata dau ra.

Ban nay co the chay theo 2 kieu:

- Local CLI: chay truc tiep tren may.
- API server: goi HTTP API de job chay tren may ao/VM.

## Yeu Cau

- Python 3.9+
- ffmpeg va ffprobe trong PATH
- Google Chrome hoac Chromium
- Internet
- OpenAI API key

Neu chay tren Azure VM co GPU, nen dung Ubuntu 22.04/24.04 va VM dong NVIDIA T4 nhu `Standard_NC4as_T4_v3` hoac cao hon.

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

Tai output:

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

## Chay Bang Docker

Docker image duoc toi uu cho chi phi thap: mac dinh dung OpenAI transcription API thay vi local Whisper, nen khong can GPU va khong cai PyTorch/Whisper trong image.
Container cung mac dinh chay Chrome headless (`HEADLESS=1`) de hop App Service/Container Apps.

Build image:

```bash
docker build -t review-film-pipeline .
```

Run API container:

```bash
docker run --rm -p 8000:8000 \
  -e OPENAI_API_KEY="YOUR_OPENAI_KEY" \
  -e PIPELINE_API_KEY="your-secret" \
  -e TRANSCRIBE_PROVIDER="openai" \
  review-film-pipeline
```

Windows PowerShell:

```powershell
docker run --rm -p 8000:8000 `
  -e OPENAI_API_KEY="YOUR_OPENAI_KEY" `
  -e PIPELINE_API_KEY="your-secret" `
  -e TRANSCRIBE_PROVIDER="openai" `
  review-film-pipeline
```

Sau do goi API nhu phan `Chay Bang API`.

Profile tiet kiem chi phi:

```text
TRANSCRIBE_PROVIDER=openai
OPENAI_TRANSCRIBE_MODEL=whisper-1
OPENAI_MODEL=gpt-4o-mini
```

Profile local Whisper, ton CPU/GPU hon:

```text
TRANSCRIBE_PROVIDER=local
WHISPER_MODEL=base|small|medium|large
```

Neu chay local Whisper trong Docker, can dung `requirements.txt` thay vi `requirements-docker.txt` va nen chay tren VM GPU. Mac dinh Docker khong cai local Whisper de image nhe va App Service/Container Apps CPU re hon.

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

App Service phu hop neu ban uu tien chi phi va dung `TRANSCRIBE_PROVIDER=openai`. Neu workload can local Whisper/GPU, Azure Container Apps GPU hoac VM GPU se hop hon.

## Cai Dat Tren Azure VM

Ubuntu:

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip ffmpeg chromium-browser
```

Neu dung GPU VM, cai NVIDIA driver theo Azure N-series GPU driver extension hoac huong dan cua Microsoft. Kiem tra:

```bash
nvidia-smi
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
- `TRANSCRIBE_PROVIDER`
- `OPENAI_TRANSCRIBE_MODEL`
- `WHISPER_MODEL`
- `TRANSLATE_WORDS_PER_MINUTE`
- `TRANSLATE_BATCH_SIZE`
- `TRANSLATE_REVIEW_PASSES`
- `MIN_VIDEO_DURATION_SECONDS`

Khuyen nghi de secret trong env:

- `OPENAI_API_KEY`
- `PIPELINE_API_KEY`

Khong commit API key that len GitHub.

## Ghi Chu

ChromeDriver local trong `driver/` chi la fallback. Neu bi lech version, Selenium Manager se tu detect Chrome va tai driver phu hop.

Tag on dinh dau tien cua ban API + local la:

```text
v1.0-local-api-base
```
