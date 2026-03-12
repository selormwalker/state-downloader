from http.server import BaseHTTPRequestHandler
import json
import os
import tempfile
import yt_dlp

COOKIE_PATH = "/tmp/ig_cookies.txt"

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")

        url        = (body.get("url") or "").strip()
        format_id  = body.get("format_id") or "bestvideo+bestaudio/best"
        ext        = body.get("ext") or "mp4"
        convert_mp3 = bool(body.get("convert_mp3"))
        title      = body.get("title") or "download"

        if not url or not url.startswith("http"):
            self._json(400, {"ok": False, "error": "Missing URL"})
            return

        # Sanitise filename
        safe = "".join(c if c.isalnum() or c in " -_" else "_" for c in title)[:60].strip()
        filename = f"{safe}.{'mp3' if convert_mp3 else ext}"

        with tempfile.TemporaryDirectory() as tmpdir:
            out_tmpl = os.path.join(tmpdir, f"{safe}.%(ext)s")

            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "noplaylist": True,
                "outtmpl": out_tmpl,
                "http_headers": {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                },
            }
            if os.path.exists(COOKIE_PATH):
                ydl_opts["cookiefile"] = COOKIE_PATH

            if convert_mp3:
                ydl_opts["format"] = "bestaudio/best"
                ydl_opts["postprocessors"] = [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "320",
                }]
            else:
                # Merge video + best audio when format is video-only
                ydl_opts["format"] = f"{format_id}+bestaudio/best/{format_id}/bestvideo+bestaudio/best"
                ydl_opts["merge_output_format"] = "mp4"

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
            except yt_dlp.utils.DownloadError as e:
                err = str(e)
                if "private" in err.lower() or "login" in err.lower():
                    msg = "This content is private or requires a login."
                else:
                    msg = f"Download failed: {err[:200]}"
                self._json(422, {"ok": False, "error": msg})
                return
            except Exception as e:
                self._json(500, {"ok": False, "error": str(e)[:200]})
                return

            # Find the output file
            filepath = None
            for f in os.listdir(tmpdir):
                filepath = os.path.join(tmpdir, f)
                filename = f
                break

            if not filepath or not os.path.exists(filepath):
                self._json(500, {"ok": False, "error": "Download produced no output file."})
                return

            # Stream file to browser
            filesize = os.path.getsize(filepath)
            mime = "audio/mpeg" if filename.endswith(".mp3") else "video/mp4"

            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(filesize))
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self._cors()
            self.end_headers()

            with open(filepath, "rb") as fh:
                while True:
                    chunk = fh.read(1024 * 64)
                    if not chunk:
                        break
                    self.wfile.write(chunk)

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
