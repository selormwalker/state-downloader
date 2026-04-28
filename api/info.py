from http.server import BaseHTTPRequestHandler
import json
import os
import yt_dlp
import shutil

COOKIE_PATH = "/tmp/ig_cookies.txt"

PLATFORM_MAP = {
    "youtube.com": "YouTube", "youtu.be": "YouTube",
    "instagram.com": "Instagram", "tiktok.com": "TikTok",
    "twitter.com": "X / Twitter", "x.com": "X / Twitter",
    "facebook.com": "Facebook", "fb.watch": "Facebook",
    "reddit.com": "Reddit", "twitch.tv": "Twitch",
    "vimeo.com": "Vimeo", "pinterest.com": "Pinterest",
    "dailymotion.com": "Dailymotion", "soundcloud.com": "SoundCloud",
    "bilibili.com": "Bilibili", "snapchat.com": "Snapchat",
    "linkedin.com": "LinkedIn", "threads.net": "Threads",
}

def detect_platform(url):
    for domain, name in PLATFORM_MAP.items():
        if domain in url:
            return name
    return "Social Media"

def fmt_duration(secs):
    if not secs: return None
    secs = int(secs)
    h, r = divmod(secs, 3600)
    m, s = divmod(r, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

def fmt_size(b):
    if not b: return None
    for unit in ["B","KB","MB","GB"]:
        if b < 1024: return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} GB"

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except:
            body = {}
        
        url = (body.get("url") or "").strip()
        if not url or not url.startswith("http"):
            self._json(400, {"ok": False, "error": "A valid URL is required."})
            return

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            },
        }

        if os.path.exists(COOKIE_PATH):
            ydl_opts["cookiefile"] = COOKIE_PATH

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

            # ── Intelligent Format Processing ──
            video_formats = []
            seen_heights = set()
            all_fmts = info.get("formats") or []

            # Filter for video formats and sort by height
            v_fmts = [f for f in all_fmts if f.get("vcodec") != "none" and f.get("height")]
            v_fmts.sort(key=lambda x: (x.get("height") or 0, x.get("tbr") or 0), reverse=True)

            for f in v_fmts:
                h = f.get("height")
                if not h or h in seen_heights: continue
                seen_heights.add(h)

                ext = f.get("ext") or "mp4"
                fps = f.get("fps")
                size = f.get("filesize") or f.get("filesize_approx")
                
                label = f"{h}p"
                if h >= 2160: qname = "4K Ultra HD"
                elif h >= 1440: qname = "2K QHD"
                elif h >= 1080: qname = "Full HD"
                elif h >= 720: qname = "HD"
                else: qname = "Standard"

                detail = f"{ext.upper()}"
                if fps and fps > 30: detail += f" {int(fps)}fps"
                if f.get("vcodec").startswith("av01"): detail += " AV1"

                video_formats.append({
                    "format_id": f["format_id"],
                    "badge": label,
                    "label": qname,
                    "detail": detail,
                    "size": fmt_size(size) or "Stream",
                    "ext": "mp4", # Preferred container
                    "best": len(video_formats) == 0
                })
                if len(video_formats) >= 6: break

            # ── Audio Processing ──
            audio_formats = [{
                "format_id": "bestaudio/best",
                "badge": "MP3",
                "label": "MP3 Audio",
                "detail": "High Quality 320kbps",
                "size": "Auto",
                "ext": "mp3",
                "convert_mp3": True,
                "best": True
            }]

            res = {
                "ok": True,
                "platform": detect_platform(url),
                "title": info.get("title") or "Untitled Media",
                "thumbnail": info.get("thumbnail"),
                "duration": fmt_duration(info.get("duration")),
                "uploader": info.get("uploader") or info.get("channel") or "Unknown",
                "video_formats": video_formats,
                "audio_formats": audio_formats,
            }
            self._json(200, res)

        except Exception as e:
            err_msg = str(e).split('\n')[0]
            self._json(422, {"ok": False, "error": f"Failed to fetch: {err_msg}"})

    def _json(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, *args):
        pass
