#!/usr/bin/env python3
import os
import sys
import json
import shutil
import subprocess
import webbrowser
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR / "src" / "generator"))
from build_app import build_application
from build_studio import get_git_metadata

def list_installed_webapps():
    apps_dir = Path.home() / "Applications"
    if not apps_dir.exists():
        return []
    items = []
    for entry in apps_dir.iterdir():
        if not entry.name.endswith(".app"):
            continue
        cfg_file = entry / "Contents" / "Resources" / "app" / "config.json"
        if cfg_file.exists():
            try:
                cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
                size_bytes = sum(
                    f.stat().st_size for f in entry.rglob("*")
                    if f.is_file() and not f.is_symlink()
                )
                items.append({
                    "name": cfg.get("name", entry.stem),
                    "url": cfg.get("url", ""),
                    "bundleId": cfg.get("bundleId", ""),
                    "width": cfg.get("width", 940),
                    "height": cfg.get("height", 923),
                    "titleBarHidden": bool(cfg.get("titleBarHidden", False)),
                    "path": str(entry),
                    "sizeMB": round(size_bytes / (1024 * 1024), 1)
                })
            except Exception:
                pass
    return items

def get_runtime_status():
    ver, sha = get_git_metadata()
    checks = [
        {"id": "python3", "name": "Python 3 Package Builder", "ok": True, "detail": sys.version.split()[0]},
        {"id": "chromium-base", "name": "Embedded Chromium Runtime (Electron.app)", "ok": (BASE_DIR / "node_modules" / "electron" / "dist" / "Electron.app").exists(), "detail": "Electron.app"},
        {"id": "icon-toolchain", "name": "macOS Icon Toolchain (sips + iconutil)", "ok": bool(shutil.which("sips") and shutil.which("iconutil")), "detail": "/usr/bin/sips · /usr/bin/iconutil"},
        {"id": "codesign", "name": "Gatekeeper Ad-Hoc Code Signing (codesign + xattr)", "ok": bool(shutil.which("codesign")), "detail": "/usr/bin/codesign"},
        {"id": "apps-dir", "name": "Install Destination (~/Applications)", "ok": True, "detail": str(Path.home() / "Applications")}
    ]
    return {
        "version": ver,
        "gitSha": sha,
        "versionDisplay": f"v{ver} ({sha})",
        "lastUpdateCheckAt": None,
        "lastUpdatedFromVersion": None,
        "chromium": "Embedded",
        "platform": sys.platform,
        "appsDir": str(Path.home() / "Applications"),
        "checks": checks
    }

class WebAppStudioHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            html_path = BASE_DIR / "src" / "studio" / "index.html"
            with open(html_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        elif self.path == "/api/apps":
            payload = json.dumps(list_installed_webapps()).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        elif self.path == "/api/runtime":
            payload = json.dumps(get_runtime_status()).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
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
                icon_preset = data.get("icon_preset")
                bundle_id = data.get("bundle_id")
                width = data.get("width", 940)
                height = data.get("height", 923)
                install = data.get("install", True)
                hidden_titlebar = data.get("hidden_titlebar", False)

                app_path = build_application(
                    name=name,
                    url=url,
                    icon=icon,
                    icon_preset=icon_preset,
                    bundle_id=bundle_id,
                    width=width,
                    height=height,
                    title_bar_hidden=hidden_titlebar,
                    install_to_apps=install
                )
                if app_path and os.path.exists(app_path):
                    subprocess.run(["/usr/bin/open", app_path], check=False)

                response = {"success": True, "path": app_path, "log": f"Built and launched {app_path}", "launched": True}
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps(response).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))
        elif self.path == "/api/update":
            ver, sha = get_git_metadata()
            updater = BASE_DIR / "src" / "generator" / "update_mac_app.sh"
            installed_app = "/Applications/WebTAPP Mac.app"
            proc = subprocess.run(
                ["/bin/zsh", str(updater), sha, installed_app],
                cwd=str(BASE_DIR),
                capture_output=True,
                text=True
            )
            msg = f"すでに最新版です (v{ver} ({sha}))" if proc.returncode == 10 else (
                "アップデート完了" if proc.returncode == 0 else f"更新確認完了 (code {proc.returncode})"
            )
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"success": proc.returncode in (0, 10, 11), "message": msg}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

def start_server(port=3123, open_browser=True):
    server = HTTPServer(("127.0.0.1", port), WebAppStudioHandler)
    url = f"http://127.0.0.1:{port}"
    print(f"\n🚀 WebTAPP Mac running at {url}")
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
