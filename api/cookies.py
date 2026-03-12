from http.server import BaseHTTPRequestHandler
import json
import os

COOKIE_PATH = "/tmp/ig_cookies.txt"

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        action = body.get("action", "save")

        if action == "clear":
            try:
                os.remove(COOKIE_PATH)
            except FileNotFoundError:
                pass
            self._json(200, {"ok": True, "message": "Cookies cleared."})
            return

        if action == "status":
            exists = os.path.exists(COOKIE_PATH)
            self._json(200, {"ok": True, "has_cookies": exists})
            return

        # action == "save"
        cookies_txt = (body.get("cookies") or "").strip()
        if not cookies_txt:
            self._json(400, {"ok": False, "error": "No cookie data provided."})
            return

        # Validate it looks like a Netscape cookie file or raw cookie string
        # Accept both formats and normalise to Netscape format
        lines = cookies_txt.splitlines()
        netscape_lines = []
        is_netscape = any(l.strip().startswith("# Netscape") or l.count("\t") >= 6 for l in lines[:5])

        if is_netscape:
            # Already proper format — write as-is with header
            if not any(l.strip().startswith("# Netscape") for l in lines):
                netscape_lines.append("# Netscape HTTP Cookie File")
            netscape_lines.extend(lines)
        else:
            # Raw "key=value; key2=value2" or "key=value\nkey=value" format
            # Convert to Netscape format for .instagram.com
            netscape_lines.append("# Netscape HTTP Cookie File")
            # Handle semicolon-separated on one line
            if ";" in cookies_txt and "\t" not in cookies_txt:
                pairs = cookies_txt.replace("\n", " ").split(";")
            else:
                pairs = [l for l in lines if "=" in l]
            for pair in pairs:
                pair = pair.strip()
                if not pair or "=" not in pair:
                    continue
                name, _, value = pair.partition("=")
                name = name.strip()
                value = value.strip()
                if not name:
                    continue
                # domain  flag  path  secure  expiry  name  value
                netscape_lines.append(f".instagram.com\tTRUE\t/\tTRUE\t9999999999\t{name}\t{value}")

        with open(COOKIE_PATH, "w") as f:
            f.write("\n".join(netscape_lines) + "\n")

        self._json(200, {"ok": True, "message": "Cookies saved. Instagram downloads are now enabled."})

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
