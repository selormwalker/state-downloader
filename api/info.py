from http.server import BaseHTTPRequestHandler
import json
import os
import yt_dlp
from urllib.parse import urlparse, parse_qs

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
    "linkedin.com": "LinkedIn",
}

def detect_platform(url):
    for domain, name in PLATFORM_MAP.items():
        if domain in url:
            return name
    return "Unknown"

def fmt_duration(secs):
    if not secs:
        return None
    secs = int(secs)
    h, r = divmod(secs, 3600)
    m, s = divmod(r, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

def fmt_size(b):
    if not b:
        return None
    for unit in ["B","KB","MB","GB"]:
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} GB"

def fmt_views(n):
    if not n:
        return None
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M views"
    if n >= 1_000:
        return f"{n/1_000:.0f}K views"
    return f"{n} views"

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        url = (body.get("url") or "").strip()

        if not url or not url.startswith("http"):
            self._json(400, {"ok": False, "error": "A valid URL is required."})
            return

        is_instagram = "instagram.com" in url

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            },
        }

        # Attach cookies if available
        if os.path.exists(COOKIE_PATH):
            ydl_opts["cookiefile"] = COOKIE_PATH
        elif is_instagram:
            self._json(401, {
                "ok": False,
                "error": "instagram_needs_cookies",
                "message": "Instagram requires login cookies to download. Click 'Add Instagram Cookies' to set them up."
            })
            return

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

            # ── Build video formats ──
            video_formats = []
            seen_heights = set()
            all_fmts = info.get("formats") or []

            for f in sorted(all_fmts, key=lambda x: (x.get("height") or 0), reverse=True):
                if f.get("vcodec") in (None, "none"):
                    continue
                height = f.get("height")
                if not height or height in seen_heights:
                    continue
                seen_heights.add(height)

                ext = f.get("ext") or "mp4"
                fps = f.get("fps")
                has_audio = f.get("acodec") not in (None, "none")
                filesize = f.get("filesize") or f.get("filesize_approx")

                if height >= 2160:   qlabel, qname = f"{height}p", "4K Ultra HD"
                elif height >= 1440: qlabel, qname = f"{height}p", "2K QHD"
                elif height >= 1080: qlabel, qname = f"{height}p", "Full HD"
                elif height >= 720:  qlabel, qname = f"{height}p", "HD"
                elif height >= 480:  qlabel, qname = f"{height}p", "Standard"
                else:                qlabel, qname = f"{height}p", "Low quality"

                detail_parts = [ext.upper()]
                if fps:
                    detail_parts.append(f"{int(fps)}fps")
                if not has_audio:
                    detail_parts.append("no audio — auto-merged")

                video_formats.append({
                    "format_id": f["format_id"],
                    "badge": qlabel,
                    "label": qname,
                    "detail": " · ".join(detail_parts),
                    "size": fmt_size(filesize) or "~auto",
                    "ext": ext,
                    "height": height,
                    "has_audio": has_audio,
                })

            # cap at 6
            video_formats = video_formats[:6]
            if video_formats:
                video_formats[0]["best"] = True

            # ── Build audio formats ──
            audio_fmts_raw = [
                f for f in all_fmts
                if f.get("vcodec") in (None, "none") and f.get("acodec") not in (None, "none")
            ]
            audio_fmts_raw.sort(key=lambda x: x.get("abr") or 0, reverse=True)

            audio_formats = []
            seen_abr = set()
            for f in audio_fmts_raw:
                abr = f.get("abr") or 0
                ext = f.get("ext") or "m4a"
                bucket = round(abr / 32) * 32
                if bucket in seen_abr:
                    continue
                seen_abr.add(bucket)

                badge = {"m4a": "AAC", "aac": "AAC", "opus": "Opus", "ogg": "OGG", "mp3": "MP3"}.get(ext, ext.upper())
                abr_str = f"{int(abr)}kbps" if abr else ""
                filesize = f.get("filesize") or f.get("filesize_approx")

                audio_formats.append({
                    "format_id": f["format_id"],
                    "badge": badge,
                    "label": "Audio track",
                    "detail": f"{ext.upper()} · {abr_str}".strip(" · "),
                    "size": fmt_size(filesize) or "~auto",
                    "ext": ext,
                })

            # Always offer MP3 conversion at top
            audio_formats.insert(0, {
                "format_id": "bestaudio/best",
                "badge": "MP3",
                "label": "MP3 (best quality)",
                "detail": "MP3 · 320kbps · converted",
                "size": "~auto",
                "ext": "mp3",
                "convert_mp3": True,
                "best": True,
            })
            audio_formats = audio_formats[:5]

            result = {
                "ok": True,
                "platform": detect_platform(url),
                "title": info.get("title") or "Media download",
                "thumbnail": info.get("thumbnail"),
                "duration": fmt_duration(info.get("duration")),
                "views": fmt_views(info.get("view_count")),
                "uploader": info.get("uploader") or info.get("channel"),
                "video_formats": video_formats,
                "audio_formats": audio_formats,
            }
            self._json(200, result)

        except yt_dlp.utils.DownloadError as e:
            err = str(e)
            if "Unsupported URL" in err:
                msg = "This URL isn't supported. Try YouTube, Instagram, TikTok, X, Reddit, etc."
            elif "private" in err.lower() or "login" in err.lower() or "checkpoint" in err.lower():
                if is_instagram:
                    self._json(401, {
                        "ok": False,
                        "error": "instagram_needs_cookies",
                        "message": "Instagram blocked this request. Your cookies may have expired — please update them."
                    })
                    return
                msg = "This content is private or requires a login."
            elif "rate" in err.lower() or "too many" in err.lower():
                msg = "Rate limited by the platform. Please try again in a moment."
            else:
                msg = "Could not fetch this media. Make sure the post is public and the URL is correct."
            self._json(422, {"ok": False, "error": msg})
        except Exception as e:
            self._json(500, {"ok": False, "error": f"Server error: {str(e)[:200]}"})

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
