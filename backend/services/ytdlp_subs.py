import os, subprocess, shutil, uuid, glob
from typing import List, Dict
import webvtt

def _env(name: str, default: str = "") -> str:
    v = os.getenv(name)
    return v if v is not None else default

def fetch_subs_via_ytdlp(url: str, lang_pref: str = "en") -> List[Dict]:
    ytdlp = _env("YT_YTDLP_PATH", "yt-dlp")
    ffmpeg = _env("YT_FFMPEG_PATH", "ffmpeg")
    cookies = _env("YT_COOKIES_FILE", "").strip() or None
    tmp_dir = _env("YT_TMP_DIR", ".cache/yt")
    os.makedirs(tmp_dir, exist_ok=True)

    if shutil.which(ytdlp) is None:
        raise RuntimeError("yt-dlp binary not found")
    if shutil.which(ffmpeg) is None:
        raise RuntimeError("ffmpeg binary not found")

    base = os.path.join(tmp_dir, f"{uuid.uuid4()}")

    def run_cmd(args):
        try:
            subprocess.run(args, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError:
            return None
        files = glob.glob(base + "*.vtt")
        return files or None

    manual = [ytdlp,"--write-subs","--skip-download","--sub-lang",lang_pref,"--sub-format","vtt","--output",base,url]
    auto   = [ytdlp,"--write-auto-subs","--skip-download","--sub-lang",lang_pref,"--sub-format","vtt","--output",base,url]
    if cookies: manual += ["--cookies", cookies]; auto += ["--cookies", cookies]

    files = run_cmd(manual) or run_cmd(auto)
    if not files:
        raise RuntimeError("yt-dlp produced no .vtt subtitles")

    vtt_path = files[0]
    segments: List[Dict] = []
    for caption in webvtt.read(vtt_path):
        def to_seconds(ts: str) -> float:
            hh, mm, ss_ms = ts.split(":")
            ss, *ms = ss_ms.split(".")
            ms = int(ms[0]) if ms else 0
            return int(hh)*3600 + int(mm)*60 + int(ss) + ms/1000.0
        start = to_seconds(caption.start)
        end   = to_seconds(caption.end)
        dur   = max(0.0, end - start)
        text  = caption.text.replace("\n"," ").strip()
        if text:
            segments.append({"text": text, "start": start, "duration": dur})

    for f in glob.glob(base + "*"):
        try: os.remove(f)
        except: pass

    if not segments:
        raise RuntimeError("Parsed .vtt but got no segments")
    return segments


