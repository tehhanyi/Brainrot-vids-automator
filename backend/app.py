"""
Brainrot Vids Automator - FastAPI Backend
Deploy this on Render / Railway / Fly.io
Requires: ffmpeg installed on the server, MinecraftBold.otf in the same directory
"""

import os
import subprocess
import sys
import shutil
import json
import threading
import uuid
import zipfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

# ── pip install fastapi uvicorn yt-dlp python-multipart ──────────────────────

app = FastAPI(title="Brainrot Vids API")

# Allow your GitHub Pages origin (update after deploying frontend)
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ── Paths ─────────────────────────────────────────────────────────────────────
FONT_FILE = os.path.join(os.path.dirname(__file__), "MinecraftBold.otf")
JOBS_DIR = Path(os.getenv("JOBS_DIR", "/tmp/brainrot_jobs"))
JOBS_DIR.mkdir(parents=True, exist_ok=True)

# In-memory store: job_id → { status, progress, error, download_url }
# For production with multiple workers, swap this for Redis
jobs: dict[str, dict] = {}


# ── Schemas ───────────────────────────────────────────────────────────────────
class GenerateRequest(BaseModel):
    youtube_url: str
    video_title: str
    clip_duration: int          # seconds per clip
    sponsor_start: Optional[str] = None   # e.g. "00:02:10"
    sponsor_end: Optional[str] = None     # e.g. "00:04:30"


# ── Helpers (ported from main.py, I/O prompts removed) ────────────────────────
def _ffmpeg(*args, **kwargs):
    """Run ffmpeg, suppressing noisy output."""
    return subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", *args],
        check=True,
        **kwargs,
    )


def wrap_title(title: str, max_line: int = 4, max_line_length: int = 15) -> str:
    words = title.split()
    lines, current = [], ""
    for word in words:
        if len(current) + len(word) + 1 <= max_line_length:
            current += word + " "
        else:
            lines.append(current.strip())
            current = word + " "
    lines.append(current.strip())
    return "\n".join(lines[:max_line])


def download_video(url: str, output_path: str):
    subprocess.run(
        [
            sys.executable, "-m", "yt_dlp",
            "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]",
            "--merge-output-format", "mp4",
            "--write-auto-sub",
            "--sub-format", "vtt",
            "--no-warnings",
            "-o", output_path,
            url,
        ],
        check=True,
        capture_output=True,
    )


def remove_ads(filename: str, cut_start: str, cut_end: str, tmp: Path):
    tmp.mkdir(parents=True, exist_ok=True)
    first = str(tmp / "first.mp4")
    second = str(tmp / "second.mp4")
    list_txt = str(tmp / "list.txt")

    _ffmpeg("-ss", "00:00:00", "-i", filename, "-to", cut_start,
            "-map", "0", "-c:v", "libx264", "-c:a", "aac",
            "-c:s", "mov_text", "-preset", "medium", "-y", first)

    _ffmpeg("-ss", cut_end, "-i", filename,
            "-map", "0", "-c:v", "libx264", "-c:a", "aac",
            "-c:s", "mov_text", "-preset", "medium", "-y", second)

    with open(list_txt, "w") as f:
        f.write("file 'first.mp4'\nfile 'second.mp4'\n")

    _ffmpeg("-f", "concat", "-safe", "0", "-i", list_txt,
            "-c:v", "libx264", "-c:a", "aac", "-c:s", "mov_text",
            "-preset", "medium", "-y", filename)


def split_video(filename: str, output_folder: str, segment_duration: int):
    os.makedirs(output_folder, exist_ok=True)
    _ffmpeg("-i", filename, "-c", "copy", "-map", "0",
            "-f", "segment", "-segment_time", str(segment_duration),
            f"{output_folder}/clip_%03d.mp4")


def generate_thumbnail(video_file: str, output_dir: str, part_number: int, title: str):
    os.makedirs(output_dir, exist_ok=True)
    wrapped = wrap_title(title, max_line=4, max_line_length=15)
    _ffmpeg(
        "-ss", "00:00:00", "-i", video_file, "-frames:v", "1",
        "-vf", (
            "crop=480:640:(in_w-480)/2:(in_h-640)/2,"
            f"drawtext=text='{wrapped}':text_shaping=1:text_align=center:"
            f"fontfile={FONT_FILE}:"
            "fontcolor=white:fontsize=40:borderw=2:bordercolor=black:"
            "x=(w-text_w)/2:y=50,"
            f"drawtext=text='Part {part_number}':"
            f"fontfile={FONT_FILE}:"
            "fontcolor=white:fontsize=80:borderw=3:bordercolor=black:"
            "x=(w-text_w)/2:y=h-200"
        ),
        "-q:v", "2",
        os.path.join(output_dir, f"part_{part_number}.jpg"),
    )


def add_captions_to_video(input_file: str, output_dir: str, total_clips: int, part_number: int, title: str):
    os.makedirs(output_dir, exist_ok=True)
    wrapped = wrap_title(title, max_line=3, max_line_length=25)
    filter_chain = (
        "split[original][blur];"
        "[blur]scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,boxblur=20:20[bg];"
        "[original]scale=1080:1080:force_original_aspect_ratio=increase[fg];"
        "[bg][fg]overlay=(W-w)/2:(H-h)/2:format=auto,"
        f"drawtext=text='{wrapped}':text_shaping=1:text_align=center:"
        f"fontfile={FONT_FILE}:"
        "fontcolor=white:fontsize=56:borderw=2:bordercolor=black:"
        "x=(w-text_w)/2:y=250"
    )
    if total_clips > 1:
        filter_chain += (
            f",drawtext=text='Part {part_number}':"
            f"fontfile={FONT_FILE}:"
            "fontcolor=white:fontsize=72:borderw=3:bordercolor=black:"
            "x=(w-text_w)/2:y=h-400"
        )
    _ffmpeg(
        "-i", input_file,
        "-vf", filter_chain,
        "-c:a", "copy", "-c:v", "libx264", "-preset", "medium", "-y",
        os.path.join(output_dir, f"part_{part_number}.mp4"),
    )


# ── Background job ─────────────────────────────────────────────────────────────
def _set(job_id: str, **kw):
    jobs[job_id].update(kw)


def run_job(job_id: str, req: GenerateRequest):
    job_dir = JOBS_DIR / job_id
    source_file = str(job_dir / "source_video.mp4")
    temp_folder = str(job_dir / "temp")
    clips_folder = str(job_dir / "clips")
    thumbs_folder = str(job_dir / "thumbnails")
    zip_path = str(job_dir / "output.zip")

    try:
        job_dir.mkdir(parents=True, exist_ok=True)

        # 1. Download
        _set(job_id, status="downloading", progress="Downloading video…")
        download_video(req.youtube_url, source_file)

        # 2. Remove sponsor segment
        if req.sponsor_start and req.sponsor_end:
            _set(job_id, progress="Removing sponsor segment…")
            remove_ads(source_file, req.sponsor_start, req.sponsor_end, job_dir / "ads_tmp")
            shutil.rmtree(str(job_dir / "ads_tmp"), ignore_errors=True)

        # 3. Split
        _set(job_id, status="processing", progress="Splitting into clips…")
        split_video(source_file, temp_folder, req.clip_duration)

        # 4. Process clips
        clip_files = sorted(f for f in os.listdir(temp_folder) if f.endswith(".mp4"))
        total = len(clip_files)

        for i, clip_file in enumerate(clip_files, start=1):
            _set(job_id, progress=f"Processing clip {i}/{total}…")
            clip_path = os.path.join(temp_folder, clip_file)
            generate_thumbnail(clip_path, thumbs_folder, part_number=i, title=req.video_title)
            add_captions_to_video(clip_path, clips_folder, total, part_number=i, title=req.video_title)

        # 5. Zip
        _set(job_id, progress="Packaging…")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in sorted(os.listdir(clips_folder)):
                zf.write(os.path.join(clips_folder, f), f"clips/{f}")
            for f in sorted(os.listdir(thumbs_folder)):
                zf.write(os.path.join(thumbs_folder, f), f"thumbnails/{f}")

        # 6. Cleanup heavy files (keep zip)
        shutil.rmtree(temp_folder, ignore_errors=True)
        shutil.rmtree(clips_folder, ignore_errors=True)
        shutil.rmtree(thumbs_folder, ignore_errors=True)
        if os.path.exists(source_file):
            os.remove(source_file)

        _set(job_id, status="done", progress="Done!", download_url=f"/download/{job_id}")

    except Exception as exc:
        _set(job_id, status="failed", progress="Failed.", error=str(exc))


# ── Routes ─────────────────────────────────────────────────────────────────────
@app.post("/generate")
def generate(req: GenerateRequest):
    """Start a video processing job. Returns job_id immediately."""
    job_id = uuid.uuid4().hex[:10]
    jobs[job_id] = {
        "status": "queued",
        "progress": "Queued…",
        "error": None,
        "download_url": None,
    }
    t = threading.Thread(target=run_job, args=(job_id, req), daemon=True)
    t.start()
    return {"job_id": job_id}


@app.get("/status/{job_id}")
def status(job_id: str):
    """Poll this endpoint to track progress."""
    if job_id not in jobs:
        return {"error": "Job not found"}
    return {"job_id": job_id, **jobs[job_id]}


@app.get("/download/{job_id}")
def download(job_id: str):
    """Download the finished zip of clips + thumbnails."""
    zip_path = JOBS_DIR / job_id / "output.zip"
    if not zip_path.exists():
        return {"error": "File not found or not ready yet"}
    return FileResponse(
        str(zip_path),
        media_type="application/zip",
        filename="brainrot_clips.zip",
    )


@app.get("/health")
def health():
    return {"ok": True}
