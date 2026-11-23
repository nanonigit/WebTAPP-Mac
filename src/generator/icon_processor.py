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

# Functional Category Icon Presets (macOS SF Symbols + Branded Gradient)
FUNCTIONAL_ICON_PRESETS = {
    "ai": {
        "symbol": "brain.head.profile",
        "color_top": (124, 58, 237),
        "color_bottom": (76, 29, 149),
        "label_ja": "AI・アシスタント",
        "label_en": "AI & Assistant"
    },
    "chat": {
        "symbol": "bubble.left.and.bubble.right.fill",
        "color_top": (37, 99, 235),
        "color_bottom": (29, 78, 216),
        "label_ja": "チャット・通話",
        "label_en": "Chat & Messaging"
    },
    "docs": {
        "symbol": "doc.text.fill",
        "color_top": (16, 185, 129),
        "color_bottom": (4, 120, 87),
        "label_ja": "ノート・ドキュメント",
        "label_en": "Notes & Docs"
    },
    "media": {
        "symbol": "play.rectangle.fill",
        "color_top": (239, 68, 68),
        "color_bottom": (185, 28, 28),
        "label_ja": "音楽・動画・メディア",
        "label_en": "Music & Video"
    },
    "dev": {
        "symbol": "terminal.fill",
        "color_top": (55, 65, 81),
        "color_bottom": (17, 24, 39),
        "label_ja": "開発・コード・Git",
        "label_en": "Developer & Code"
    },
    "analytics": {
        "symbol": "chart.bar.xaxis",
        "color_top": (245, 158, 11),
        "color_bottom": (180, 83, 9),
        "label_ja": "ダッシュボード・分析",
        "label_en": "Analytics & Finance"
    },
    "shop": {
        "symbol": "cart.fill",
        "color_top": (236, 72, 153),
        "color_bottom": (190, 24, 93),
        "label_ja": "EC・ショッピング",
        "label_en": "Shopping & Store"
    },
    "web": {
        "symbol": "globe",
        "color_top": (14, 165, 233),
        "color_bottom": (3, 105, 161),
        "label_ja": "汎用Webツール",
        "label_en": "General Web App"
    }
}

def get_temp_dir(prefix="webtoapp_"):
    os.makedirs(LOCAL_TMP_DIR, exist_ok=True)
    return tempfile.mkdtemp(prefix=prefix, dir=str(LOCAL_TMP_DIR))

class IconHTMLParser(HTMLParser):
    def __init__(self, base_url):
        super().__init__()
        self.base_url = base_url
        self.apple_touch_icons = []
        self.favicons = []
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

def fetch_url_content(url, timeout=10):
    ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
    # 1. Try native /usr/bin/curl first (uses macOS Keychain SSL & modern TLS)
    curl_bin = "/usr/bin/curl" if os.path.exists("/usr/bin/curl") else shutil.which("curl")
    if curl_bin:
        try:
            proc = subprocess.run(
                [curl_bin, "-fsSL", "--max-time", str(timeout), "-A", ua, url],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=timeout + 2
            )
            if proc.returncode == 0 and proc.stdout:
                return proc.stdout
        except Exception:
            pass

    # 2. Fallback to urllib (with unverified SSL context if macOS Python lacks certifi)
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.read()
    except Exception:
        try:
            import ssl
            ctx = ssl._create_unverified_context()
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as response:
                return response.read()
        except Exception:
            return None

def download_image(url, output_path, timeout=10):
    content = fetch_url_content(url, timeout)
    if not content:
        return False
    with open(output_path, "wb") as f:
        f.write(content)
    return True

def get_best_icon_url(web_url):
    """
    Prioritizes true square favicons and Apple Touch Icons (excludes wide rectangular OG banners).
    """
    parsed = urllib.parse.urlparse(web_url)
    domain = parsed.netloc
    
    html_data = fetch_url_content(web_url)
    candidate_urls = []
    
    if html_data:
        try:
            html_text = html_data.decode("utf-8", errors="ignore")
            parser = IconHTMLParser(web_url)
            parser.feed(html_text)
            
            # 1. Apple Touch Icons (Square, High-Res)
            for href, _ in parser.apple_touch_icons:
                candidate_urls.append(href)

            # 2. Manifest square icons
            if parser.manifest_url:
                manifest_data = fetch_url_content(parser.manifest_url)
                if manifest_data:
                    try:
                        manifest_json = json.loads(manifest_data.decode("utf-8", errors="ignore"))
                        icons = manifest_json.get("icons", [])
                        for ic in sorted(
                            icons,
                            key=lambda x: int(x.get("sizes", "0").split("x")[0])
                            if "x" in x.get("sizes", "") and x.get("sizes", "").split("x")[0].isdigit()
                            else 0,
                            reverse=True
                        ):
                            src = ic.get("src")
                            if src:
                                candidate_urls.append(urllib.parse.urljoin(parser.manifest_url, src))
                    except Exception:
                        pass

            # 3. Declared Favicons (<link rel="icon">)
            for href, _ in parser.favicons:
                candidate_urls.append(href)
        except Exception:
            pass

    # 4. High-res Google S2 Favicon API (256x256 square)
    if domain:
        candidate_urls.append(f"https://www.google.com/s2/favicons?domain={domain}&sz=256")
        # 5. Root /favicon.ico
        candidate_urls.append(f"{parsed.scheme or 'https'}://{domain}/favicon.ico")

    return candidate_urls

def create_functional_category_png(filename, category_key="web", width=1024, height=1024, app_name="App"):
    """
    Renders a native macOS squircle icon with an SF Symbol (via AppKit) or
    clean Pillow monogram fallback when AppKit is unavailable.
    """
    preset = FUNCTIONAL_ICON_PRESETS.get(category_key, FUNCTIONAL_ICON_PRESETS["web"])
    r1, g1, b1 = preset["color_top"]
    r2, g2, b2 = preset["color_bottom"]
    symbol_name = preset["symbol"]

    try:
        import AppKit
        import Foundation

        rep = AppKit.NSBitmapImageRep.alloc().initWithBitmapDataPlanes_pixelsWide_pixelsHigh_bitsPerSample_samplesPerPixel_hasAlpha_isPlanar_colorSpaceName_bytesPerRow_bitsPerPixel_(
            None, width, height, 8, 4, True, False, AppKit.NSCalibratedRGBColorSpace, 0, 0
        )
        ctx = AppKit.NSGraphicsContext.graphicsContextWithBitmapImageRep_(rep)
        AppKit.NSGraphicsContext.saveGraphicsState()
        AppKit.NSGraphicsContext.setCurrentContext_(ctx)

        # Draw macOS icon squircle with padding
        pad = width * 0.08
        rect = Foundation.NSMakeRect(pad, pad, width - pad * 2, height - pad * 2)
        radius = (width - pad * 2) * 0.225
        path = AppKit.NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(rect, radius, radius)

        c_top = AppKit.NSColor.colorWithCalibratedRed_green_blue_alpha_(r1 / 255.0, g1 / 255.0, b1 / 255.0, 1.0)
        c_bot = AppKit.NSColor.colorWithCalibratedRed_green_blue_alpha_(r2 / 255.0, g2 / 255.0, b2 / 255.0, 1.0)
        grad = AppKit.NSGradient.alloc().initWithStartingColor_endingColor_(c_bot, c_top)
        grad.drawInBezierPath_angle_(path, 90.0)

        # Subtle inner border
        AppKit.NSColor.colorWithCalibratedWhite_alpha_(1.0, 0.18).setStroke()
        path.setLineWidth_(width * 0.012)
        path.stroke()

        # Draw SF Symbol in white
        sym_img = AppKit.NSImage.imageWithSystemSymbolName_accessibilityDescription_(symbol_name, None)
        if sym_img is not None:
            cfg = AppKit.NSImageSymbolConfiguration.configurationWithPointSize_weight_(width * 0.38, AppKit.NSFontWeightSemibold)
            white_cfg = AppKit.NSImageSymbolConfiguration.configurationWithHierarchicalColor_(AppKit.NSColor.whiteColor())
            cfg = cfg.configurationByApplyingConfiguration_(white_cfg)
            styled = sym_img.imageWithSymbolConfiguration_(cfg)
            if styled is not None:
                sz = styled.size()
                dx = (width - sz.width) / 2.0
                dy = (height - sz.height) / 2.0
                styled.drawInRect_fromRect_operation_fraction_(
                    Foundation.NSMakeRect(dx, dy, sz.width, sz.height),
                    Foundation.NSZeroRect,
                    AppKit.NSCompositingOperationSourceOver,
                    0.96
                )

        AppKit.NSGraphicsContext.restoreGraphicsState()
        png_data = rep.representationUsingType_properties_(AppKit.NSBitmapImageFileTypePNG, {})
        png_data.writeToFile_atomically_(str(filename), True)
        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            return True
    except Exception:
        pass

    # Fallback using Pillow with clean monogram letter
    try:
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        pad = int(width * 0.07)
        radius = int(width * 0.19)
        draw.rounded_rectangle([pad, pad, width - pad, height - pad], radius=radius, fill=(r1, g1, b1, 255))
        glyph_map = {
            "ai": "AI", "chat": "💬", "docs": "D", "media": "▶",
            "dev": "</>", "analytics": "📊", "shop": "S", "web": (app_name[:1].upper() if app_name else "W")
        }
        glyph = glyph_map.get(category_key, app_name[:1].upper() if app_name else "W")
        font = ImageFont.load_default()
        for fp in ["/System/Library/Fonts/Helvetica.ttc", "/System/Library/Fonts/SFNS.ttf"]:
            if os.path.exists(fp):
                try:
                    font = ImageFont.truetype(fp, size=int(width * 0.40))
                    break
                except Exception:
                    pass
        bbox = draw.textbbox((0, 0), glyph, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(((width - tw) / 2 - bbox[0], (height - th) / 2 - bbox[1]), glyph, font=font, fill=(255, 255, 255, 255))
        img.save(filename, "PNG")
        return True
    except Exception:
        pass

    create_pure_fallback_png(filename, category_key, 512, 512, (r1, g1, b1), (r2, g2, b2))
    return True

def create_pure_fallback_png(filename, name="App", width=512, height=512, custom_top=None, custom_bottom=None):
    """
    Creates a rounded icon PNG with smooth gradient in pure Python (zero dependencies).
    """
    if custom_top and custom_bottom:
        color_top, color_bottom = custom_top, custom_bottom
    else:
        hash_val = sum(ord(c) for c in name)
        palettes = [
            ((37, 99, 235), (29, 78, 216)),
            ((16, 185, 129), (5, 150, 105)),
            ((139, 92, 246), (109, 40, 217)),
            ((239, 68, 68), (185, 28, 28)),
            ((245, 158, 11), (217, 119, 6)),
            ((55, 65, 81), (17, 24, 39)),
        ]
        color_top, color_bottom = palettes[hash_val % len(palettes)]

    radius = int(width * 0.22)
    raw_data = bytearray()

    for y in range(height):
        raw_data.append(0)
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

def normalize_to_macos_squircle(master_png_path, size=1024):
    """
    Normalizes any favicon or uploaded image into a full-size native macOS squircle icon
    (880x880 rounded-rect inside 1024x1024 canvas, matching official macOS apps).
    Eliminates tiny centered badges and excessive padding in the macOS Dock.
    """
    try:
        from PIL import Image, ImageChops, ImageDraw
    except ImportError:
        return False

    try:
        src = Image.open(master_png_path).convert("RGBA")
        w, h = src.size
        if w == 0 or h == 0:
            return False

        # 1. Inspect alpha channel to see if image is transparent/circular or full-bleed
        alpha = src.getchannel("A")
        alpha_extrema = alpha.getextrema()
        has_transparency = alpha_extrema[0] < 240

        # Sample corners and edge midpoints to detect uniform background color
        corners = [
            src.getpixel((0, 0)),
            src.getpixel((w - 1, 0)),
            src.getpixel((0, h - 1)),
            src.getpixel((w - 1, h - 1)),
        ]
        opaque_corners = [c for c in corners if c[3] > 200]

        def color_dist(c1, c2):
            return abs(c1[0] - c2[0]) + abs(c1[1] - c2[1]) + abs(c1[2] - c2[2])

        # Determine squircle background fill color
        bg_color = (255, 255, 255, 255)
        is_uniform_opaque_bg = False

        if len(opaque_corners) >= 3:
            ref = opaque_corners[0]
            if all(color_dist(ref, c) < 28 for c in opaque_corners):
                bg_color = (ref[0], ref[1], ref[2], 255)
                is_uniform_opaque_bg = True

        # Check if it's a circular badge (transparent corners, opaque ring around center)
        if not is_uniform_opaque_bg and has_transparency:
            # Sample ring pixels at 15% inset from edges
            ring_pts = [
                src.getpixel((int(w * 0.5), int(h * 0.14))),
                src.getpixel((int(w * 0.5), int(h * 0.86))),
                src.getpixel((int(w * 0.14), int(h * 0.5))),
                src.getpixel((int(w * 0.86), int(h * 0.5))),
            ]
            opaque_ring = [c for c in ring_pts if c[3] > 200]
            if len(opaque_ring) >= 3:
                ref = opaque_ring[0]
                if all(color_dist(ref, c) < 28 for c in opaque_ring):
                    bg_color = (ref[0], ref[1], ref[2], 255)
                    is_uniform_opaque_bg = True

        # 2. Find tight bounding box of the foreground logo
        # First trim transparent outer margin
        alpha_bbox = alpha.point(lambda p: 255 if p > 20 else 0).getbbox()
        if alpha_bbox:
            cropped = src.crop(alpha_bbox)
        else:
            cropped = src

        cw, ch = cropped.size

        # If we detected a uniform background color (e.g. white circle or white square),
        # find the inner foreground logo bbox by diffing against bg_color
        inner_cropped = cropped
        if is_uniform_opaque_bg:
            flat_bg = Image.new("RGBA", (cw, ch), bg_color)
            # Composite cropped onto bg_color so transparent corners become bg_color
            comp = Image.alpha_composite(flat_bg, cropped)
            diff = ImageChops.difference(comp.convert("RGB"), flat_bg.convert("RGB"))
            # Threshold subtle anti-aliasing noise
            mask = diff.convert("L").point(lambda p: 255 if p > 22 else 0)
            fg_bbox = mask.getbbox()
            if fg_bbox:
                fw = fg_bbox[2] - fg_bbox[0]
                fh = fg_bbox[3] - fg_bbox[1]
                # Only use inner foreground crop if it's meaningful (>15% of size)
                if fw > cw * 0.15 and fh > ch * 0.15:
                    inner_cropped = comp.crop(fg_bbox)

        # 3. Render onto standard macOS squircle canvas (880x880 inside 1024x1024)
        pad = 72
        card_size = size - pad * 2  # 880
        radius = 196

        canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        squircle_mask = Image.new("L", (size, size), 0)
        mask_draw = ImageDraw.Draw(squircle_mask)
        mask_draw.rounded_rectangle([pad, pad, size - pad, size - pad], radius=radius, fill=255)

        card = Image.new("RGBA", (size, size), bg_color)

        iw, ih = inner_cropped.size
        # Decide whether to full-bleed (for full-bleed photo/gradient icons) or upscale logo
        is_full_bleed = (
            not has_transparency
            and not is_uniform_opaque_bg
            and iw >= w * 0.85
            and ih >= h * 0.85
        )

        if is_full_bleed:
            resized = inner_cropped.resize((card_size, card_size), Image.Resampling.LANCZOS)
            card.paste(resized, (pad, pad), resized)
        else:
            # Scale logo generously to fill ~74% of the squircle card (matches official ChatGPT.app)
            target_box = int(card_size * 0.74)
            scale = min(target_box / float(iw), target_box / float(ih))
            new_w = max(1, int(round(iw * scale)))
            new_h = max(1, int(round(ih * scale)))
            resized = inner_cropped.resize((new_w, new_h), Image.Resampling.LANCZOS)
            ox = (size - new_w) // 2
            oy = (size - new_h) // 2
            card.paste(resized, (ox, oy), resized)

        # Apply macOS squircle mask & subtle border for crisp edge definition
        final_img = Image.composite(card, canvas, squircle_mask)
        border_draw = ImageDraw.Draw(final_img)
        border_draw.rounded_rectangle(
            [pad, pad, size - pad, size - pad],
            radius=radius,
            outline=(0, 0, 0, 28),
            width=4
        )
        final_img.save(master_png_path, "PNG")
        return True
    except Exception:
        return False


def convert_image_to_icns(source_image_path, output_icns_path, app_name="App", normalize_squircle=True):
    if source_image_path and os.path.exists(source_image_path) and source_image_path.lower().endswith(".icns"):
        os.makedirs(os.path.dirname(os.path.abspath(output_icns_path)), exist_ok=True)
        shutil.copy2(source_image_path, output_icns_path)
        return os.path.exists(output_icns_path) and os.path.getsize(output_icns_path) > 0

    temp_dir = get_temp_dir(prefix="webtoapp_icon_")
    try:
        master_png = os.path.join(temp_dir, "master.png")
        
        if source_image_path and os.path.exists(source_image_path) and os.path.getsize(source_image_path) > 0:
            convert_cmd = ["sips", "-s", "format", "png", source_image_path, "--out", master_png]
            subprocess.run(convert_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        if not os.path.exists(master_png) or os.path.getsize(master_png) == 0:
            create_functional_category_png(master_png, "web")
        elif normalize_squircle:
            # Normalize fetched favicons / custom images to full-size macOS squircle
            normalize_to_macos_squircle(master_png, size=1024)

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

def generate_icon_for_app(web_url, app_name, custom_icon_path, output_icns_path, icon_preset=None):
    # Mode 1: Custom uploaded icon file
    if custom_icon_path and os.path.exists(custom_icon_path):
        print(f"[*] Using custom uploaded icon: {custom_icon_path}")
        return convert_image_to_icns(custom_icon_path, output_icns_path, app_name)

    # Mode 2: Functional category icon preset (ai, chat, docs, media, dev, analytics, shop, web)
    if icon_preset and icon_preset in FUNCTIONAL_ICON_PRESETS:
        print(f"[*] Generating functional category icon preset: '{icon_preset}'...")
        temp_dir = get_temp_dir(prefix="webtoapp_preset_")
        try:
            preset_png = os.path.join(temp_dir, "preset.png")
            create_functional_category_png(preset_png, icon_preset)
            return convert_image_to_icns(preset_png, output_icns_path, app_name, normalize_squircle=False)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    # Mode 3 (Default): Extract website Favicon / Apple Touch Icon
    print(f"[*] Fetching website Favicon for {web_url}...")
    candidate_urls = get_best_icon_url(web_url)
    
    temp_dir = get_temp_dir(prefix="webtoapp_download_")
    try:
        downloaded = False
        download_target = os.path.join(temp_dir, "downloaded_icon")
        
        for cand_url in candidate_urls:
            if download_image(cand_url, download_target) and os.path.getsize(download_target) > 100:
                downloaded = True
                print(f"[+] Downloaded Favicon successfully from {cand_url}")
                break
        
        if downloaded:
            success = convert_image_to_icns(download_target, output_icns_path, app_name)
            if success:
                return True

        print(f"[*] Creating fallback functional icon for '{app_name}'...")
        fallback_png = os.path.join(temp_dir, "fallback.png")
        create_functional_category_png(fallback_png, "web", app_name=app_name)
        return convert_image_to_icns(fallback_png, output_icns_path, app_name, normalize_squircle=False)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: icon_processor.py <URL> <App Name> <Output.icns> [custom_icon_path] [icon_preset]")
        sys.exit(1)
    
    url = sys.argv[1]
    name = sys.argv[2]
    out_icns = sys.argv[3]
    custom_icon = sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] != "-" else None
    preset = sys.argv[5] if len(sys.argv) > 5 else None
    
    ok = generate_icon_for_app(url, name, custom_icon, out_icns, preset)
    if ok:
        print(f"[+] Icon saved to: {out_icns}")
    else:
        print("[-] Failed to generate icon")
        sys.exit(1)
