import os
import subprocess
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parent
JOBS_DIR = PROJECT_ROOT / "jobs"
API_KEY = os.getenv("PIPELINE_API_KEY", "")

app = FastAPI(title="Review Film Pipeline API", version="1.0.0")
executor = ThreadPoolExecutor(max_workers=1)
jobs = {}


class RunRequest(BaseModel):
    urls: List[str] = Field(..., min_length=1)
    keep_temp: bool = False


class RunResponse(BaseModel):
    job_id: str
    status: str
    status_url: str


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def require_api_key(x_api_key: Optional[str] = Header(default=None)):
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


def update_job(job_id, **updates):
    jobs[job_id].update(updates)
    jobs[job_id]["updated_at"] = now_iso()


def run_pipeline_job(job_id, keep_temp):
    job_dir = JOBS_DIR / job_id
    urls_file = job_dir / "urls.txt"
    output_dir = job_dir / "output"
    log_path = job_dir / "run.log"
    command = [
        sys.executable,
        str(PROJECT_ROOT / "main.py"),
        "-r",
        str(urls_file),
        "-o",
        str(output_dir),
    ]
    if keep_temp:
        command.append("--keep-temp")

    update_job(job_id, status="running", started_at=now_iso())
    with open(log_path, "w", encoding="utf-8") as log_file:
        process = subprocess.run(
            command,
            cwd=str(PROJECT_ROOT),
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
        )

    files = sorted(path.name for path in output_dir.glob("*.mp4")) if output_dir.exists() else []
    if process.returncode == 0:
        update_job(job_id, status="done", finished_at=now_iso(), files=files)
    else:
        update_job(
            job_id,
            status="failed",
            finished_at=now_iso(),
            returncode=process.returncode,
            files=files,
        )


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/run", response_model=RunResponse, dependencies=[Depends(require_api_key)])
def run(request: RunRequest):
    job_id = uuid.uuid4().hex
    job_dir = JOBS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    urls_file = job_dir / "urls.txt"
    urls_file.write_text("\n".join(request.urls) + "\n", encoding="utf-8")

    jobs[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "files": [],
        "log_url": f"/jobs/{job_id}/log",
    }
    executor.submit(run_pipeline_job, job_id, request.keep_temp)
    return RunResponse(job_id=job_id, status="queued", status_url=f"/jobs/{job_id}")


@app.get("/jobs/{job_id}", dependencies=[Depends(require_api_key)])
def get_job(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    job = dict(jobs[job_id])
    job["download_urls"] = [
        f"/jobs/{job_id}/files/{file_name}"
        for file_name in job.get("files", [])
    ]
    return job


@app.get("/jobs/{job_id}/log", dependencies=[Depends(require_api_key)])
def get_log(job_id: str):
    log_path = JOBS_DIR / job_id / "run.log"
    if not log_path.exists():
        raise HTTPException(status_code=404, detail="Log not found")
    return FileResponse(str(log_path), media_type="text/plain", filename="run.log")


@app.get("/jobs/{job_id}/files/{file_name}", dependencies=[Depends(require_api_key)])
def download_file(job_id: str, file_name: str):
    if "/" in file_name or "\\" in file_name:
        raise HTTPException(status_code=400, detail="Invalid file name")
    file_path = JOBS_DIR / job_id / "output" / file_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(str(file_path), media_type="video/mp4", filename=file_name)
