#!/usr/bin/env python3
import os
import sys
import json
import webbrowser
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR / "src" / "generator"))
from build_app import build_application

class WebAppStudioHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            html_path = BASE_DIR / "gui" / "index.html"
            with open(html_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/api/build":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode("utf-8"))
                name = data.get("name")
                url = data.get("url")
                icon = data.get("icon")
                bundle_id = data.get("bundle_id")
                width = data.get("width", 1200)
                height = data.get("height", 800)
                install = data.get("install", True)
                hidden_titlebar = data.get("hidden_titlebar", False)

                app_path = build_application(
                    name=name,
                    url=url,
                    icon=icon,
                    bundle_id=bundle_id,
                    width=width,
                    height=height,
                    title_bar_hidden=hidden_titlebar,
                    install_to_apps=install
                )

                response = {"success": True, "path": app_path}
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps(response).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

def start_server(port=3123, open_browser=True):
    server = HTTPServer(("127.0.0.1", port), WebAppStudioHandler)
    url = f"http://127.0.0.1:{port}"
    print(f"\n🚀 Web-to-App Studio running at {url}")
    print("Press Ctrl+C to stop.\n")
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        server.server_close()

if __name__ == "__main__":
    start_server()
