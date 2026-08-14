#!/usr/bin/env python3
import os
import sys
import re
import json
import zlib
import struct
import shutil
import tempfile
import subprocess
import urllib.request
import urllib.parse
from pathlib import Path
from html.parser import HTMLParser

BASE_DIR = Path(__file__).resolve().parent.parent.parent
LOCAL_TMP_DIR = BASE_DIR / ".tmp"

def get_temp_dir(prefix="webtoapp_"):
    os.makedirs(LOCAL_TMP_DIR, exist_ok=True)
    return tempfile.mkdtemp(prefix=prefix, dir=str(LOCAL_TMP_DIR))

class IconHTMLParser(HTMLParser):
    def __init__(self, base_url):
        super().__init__()
        self.base_url = base_url
        self.apple_touch_icons = []
        self.favicons = []
        self.og_images = []
        self.manifest_url = None

    def handle_starttag(self, tag, attrs):
        attrs_dict = {k.lower(): v for k, v in attrs if v is not None}
        if tag == "link":
            rel = attrs_dict.get("rel", "").lower().split()
            href = attrs_dict.get("href")
            if not href:
                return
            full_href = urllib.parse.urljoin(self.base_url, href)
            sizes = attrs_dict.get("sizes", "")
            
            if "apple-touch-icon" in rel or "apple-touch-icon-precomposed" in rel:
                self.apple_touch_icons.append((full_href, sizes))
            elif "icon" in rel or "shortcut" in rel:
                self.favicons.append((full_href, sizes))
            elif "manifest" in rel:
                self.manifest_url = full_href

        elif tag == "meta":
            prop = attrs_dict.get("property", "").lower()
            name = attrs_dict.get("name", "").lower()
            content = attrs_dict.get("content")
            if not content:
                return
            full_content = urllib.parse.urljoin(self.base_url, content)
            if prop == "og:image" or name == "twitter:image":
                self.og_images.append(full_content)

def fetch_url_content(url, timeout=10):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.read()
    except Exception as e:
        return None

def download_image(url, output_path, timeout=10):
    content = fetch_url_content(url, timeout)
    if not content:
        return False
    with open(output_path, "wb") as f:
        f.write(content)
    return True

def get_best_icon_url(web_url):
    parsed = urllib.parse.urlparse(web_url)
    domain = parsed.netloc
    
    html_data = fetch_url_content(web_url)
    candidate_urls = []
    
    if html_data:
        try:
            html_text = html_data.decode("utf-8", errors="ignore")
            parser = IconHTMLParser(web_url)
            parser.feed(html_text)
            
            # 1. Manifest icons
            if parser.manifest_url:
                manifest_data = fetch_url_content(parser.manifest_url)
                if manifest_data:
                    try:
                        manifest_json = json.loads(manifest_data.decode("utf-8", errors="ignore"))
                        icons = manifest_json.get("icons", [])
                        for ic in sorted(icons, key=lambda x: int(x.get("sizes", "0").split("x")[0]) if "x" in x.get("sizes", "") and x.get("sizes", "").split("x")[0].isdigit() else 0, reverse=True):
                            src = ic.get("src")
                            if src:
                                candidate_urls.append(urllib.parse.urljoin(parser.manifest_url, src))
                    except Exception:
                        pass

            # 2. Apple Touch Icons
            for href, sizes in parser.apple_touch_icons:
                candidate_urls.append(href)
                
            # 3. OpenGraph / Twitter Images
            for href in parser.og_images:
                candidate_urls.append(href)
                
            # 4. Standard Favicons
            for href, sizes in parser.favicons:
                candidate_urls.append(href)
        except Exception:
            pass

    # 5. Fallback: Google Favicon service (256px)
    candidate_urls.append(f"https://www.google.com/s2/favicons?domain={domain}&sz=256")
    # 6. Fallback: standard /favicon.ico
    candidate_urls.append(f"{parsed.scheme}://{domain}/favicon.ico")

    return candidate_urls

def create_pure_fallback_png(filename, name="App", width=512, height=512):
    """
    Creates a beautiful rounded icon PNG with smooth gradient in pure Python (zero dependencies).
    """
    # Color palette based on name hash
    hash_val = sum(ord(c) for c in name)
    palettes = [
        ((37, 99, 235), (29, 78, 216)),    # Blue (NotebookLM / Messenger)
        ((16, 185, 129), (5, 150, 105)),   # Emerald / Green (ChatGPT)
        ((139, 92, 246), (109, 40, 217)),  # Purple / Violet (Claude)
        ((239, 68, 68), (185, 28, 28)),    # Red (YouTube)
        ((245, 158, 11), (217, 119, 6)),   # Amber
        ((55, 65, 81), (17, 24, 39)),      # Dark Gray (Notion)
    ]
    color_top, color_bottom = palettes[hash_val % len(palettes)]

    radius = int(width * 0.22)
    raw_data = bytearray()

    for y in range(height):
        raw_data.append(0) # Filter byte 0 (None)
        t = y / (height - 1)
        cr = int(color_top[0] + (color_bottom[0] - color_top[0]) * t)
        cg = int(color_top[1] + (color_bottom[1] - color_top[1]) * t)
        cb = int(color_top[2] + (color_bottom[2] - color_top[2]) * t)

        for x in range(width):
            dx = max(0, max(radius - x, x - (width - 1 - radius)))
            dy = max(0, max(radius - y, y - (height - 1 - radius)))
            dist_sq = dx * dx + dy * dy
            if dist_sq > radius * radius:
                raw_data.extend([0, 0, 0, 0])
            else:
                raw_data.extend([cr, cg, cb, 255])

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    compressed = zlib.compress(bytes(raw_data), 9)
    png_data = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", compressed) + chunk(b"IEND", b"")

    with open(filename, "wb") as f:
        f.write(png_data)

def convert_image_to_icns(source_image_path, output_icns_path, app_name="App"):
    temp_dir = get_temp_dir(prefix="webtoapp_icon_")
    try:
        master_png = os.path.join(temp_dir, "master.png")
        
        # Check if source is already a valid image
        if os.path.exists(source_image_path) and os.path.getsize(source_image_path) > 0:
            convert_cmd = ["sips", "-s", "format", "png", source_image_path, "--out", master_png]
            subprocess.run(convert_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        if not os.path.exists(master_png) or os.path.getsize(master_png) == 0:
            create_pure_fallback_png(master_png, app_name)

        iconset_dir = os.path.join(temp_dir, "AppIcon.iconset")
        os.makedirs(iconset_dir, exist_ok=True)

        sizes = [
            ("icon_16x16.png", 16),
            ("icon_16x16@2x.png", 32),
            ("icon_32x32.png", 32),
            ("icon_32x32@2x.png", 64),
            ("icon_128x128.png", 128),
            ("icon_128x128@2x.png", 256),
            ("icon_256x256.png", 256),
            ("icon_256x256@2x.png", 512),
            ("icon_512x512.png", 512),
            ("icon_512x512@2x.png", 1024)
        ]

        for filename, size in sizes:
            target_path = os.path.join(iconset_dir, filename)
            subprocess.run([
                "sips",
                "-z", str(size), str(size),
                master_png,
                "--out", target_path
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Produce .icns using iconutil
        os.makedirs(os.path.dirname(os.path.abspath(output_icns_path)), exist_ok=True)
        subprocess.run([
            "iconutil",
            "-c", "icns",
            iconset_dir,
            "-o", output_icns_path
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

        return os.path.exists(output_icns_path) and os.path.getsize(output_icns_path) > 0
    except Exception as e:
        print(f"[Error] Failed to create .icns: {e}", file=sys.stderr)
        return False
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

def generate_icon_for_app(web_url, app_name, custom_icon_path, output_icns_path):
    if custom_icon_path and os.path.exists(custom_icon_path):
        print(f"[*] Using custom icon: {custom_icon_path}")
        return convert_image_to_icns(custom_icon_path, output_icns_path, app_name)

    print(f"[*] Searching for web icon for {web_url}...")
    candidate_urls = get_best_icon_url(web_url)
    
    temp_dir = get_temp_dir(prefix="webtoapp_download_")
    try:
        downloaded = False
        download_target = os.path.join(temp_dir, "downloaded_icon")
        
        for cand_url in candidate_urls:
            if download_image(cand_url, download_target) and os.path.getsize(download_target) > 200:
                downloaded = True
                print(f"[+] Downloaded icon successfully from {cand_url}")
                break
        
        if downloaded:
            success = convert_image_to_icns(download_target, output_icns_path, app_name)
            if success:
                return True

        # Fallback to generated icon
        print(f"[*] Creating branded fallback icon for '{app_name}'...")
        fallback_png = os.path.join(temp_dir, "fallback.png")
        create_pure_fallback_png(fallback_png, app_name)
        return convert_image_to_icns(fallback_png, output_icns_path, app_name)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: icon_processor.py <URL> <App Name> <Output.icns> [custom_icon_path]")
        sys.exit(1)
    
    url = sys.argv[1]
    name = sys.argv[2]
    out_icns = sys.argv[3]
    custom_icon = sys.argv[4] if len(sys.argv) > 4 else None
    
    ok = generate_icon_for_app(url, name, custom_icon, out_icns)
    if ok:
        print(f"[+] Icon saved to: {out_icns}")
    else:
        print("[-] Failed to generate icon")
        sys.exit(1)
