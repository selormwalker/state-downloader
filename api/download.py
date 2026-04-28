from http.server import BaseHTTPRequestHandler
import json
import os
import subprocess
import shutil
import urllib.parse

# Path to cookies if provided by user
COOKIE_PATH = "/tmp/ig_cookies.txt"

def get_yt_dlp_path():
    # Try to find yt-dlp in path
    path = shutil.which("yt-dlp")
    if path:
        return path
    return "yt-dlp"

def build_format_arg(format_id, convert_mp3):
    if convert_mp3:
        return "bestaudio/best"
    # Smart merging logic: try to get the requested format + best audio, 
    # or fallback to just the format, or finally best overall.
    return f"{format_id}+bestaudio/best/{format_id}/bestvideo+bestaudio/best"

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

        url         = (body.get("url") or "").strip()
        format_id   = body.get("format_id") or "bestvideo+bestaudio/best"
        ext         = body.get("ext") or "mp4"
        convert_mp3  = bool(body.get("convert_mp3"))
        title       = body.get("title") or "download"

        if not url or not url.startswith("http"):
            self._json(400, {"ok": False, "error": "Missing URL"})
            return

        # 1. Prepare filename and headers
        safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in title)[:80].strip()
        final_ext = "mp3" if convert_mp3 else "mp4" # Force mp4 for compatibility in streaming
        filename = f"{safe_title}.{final_ext}"
        mime = "audio/mpeg" if convert_mp3 else "video/mp4"

        # 2. Build yt-dlp command for streaming to stdout
        cmd = [
            get_yt_dlp_path(),
            url,
            "--no-playlist",
            "--no-warnings",
            "-f", build_format_arg(format_id, convert_mp3),
            "-o", "-", # Stream to stdout
        ]

        if os.path.exists(COOKIE_PATH):
            cmd.extend(["--cookiefile", COOKIE_PATH])

        if convert_mp3:
            cmd.extend(["--extract-audio", "--audio-format", "mp3", "--audio-quality", "0", "--add-metadata", "--embed-thumbnail"])
        else:
            cmd.extend(["--merge-output-format", "mp4"])

        # 3. Start streaming response
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Disposition", f'attachment; filename="{urllib.parse.quote(filename)}"')
        self.send_header("X-Content-Type-Options", "nosniff")
        self._cors()
        self.end_headers()

        try:
            # Spawn yt-dlp and pipe its output directly to the client
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Read from stdout in chunks and write to response
            while True:
                chunk = process.stdout.read(1024 * 128) # 128KB chunks
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except (ConnectionResetError, BrokenPipeError):
                    # Client disconnected
                    process.kill()
                    break
            
            process.wait()
        except Exception as e:
            # If headers weren't sent, we could send an error, but here they are already sent
            print(f"Streaming error: {e}")

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
