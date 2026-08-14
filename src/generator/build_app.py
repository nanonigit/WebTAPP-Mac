#!/usr/bin/env python3
import os
import sys
import re
import json
import shutil
import argparse
import subprocess
from pathlib import Path

# Import local icon processor
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from icon_processor import generate_icon_for_app, convert_image_to_icns

def sanitize_name(name):
    # Remove invalid filesystem characters
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

def create_bundle_id(name):
    slug = re.sub(r'[^a-zA-Z0-9]', '', name).lower()
    return f"com.webtoapp.{slug}"

def ensure_binary(template_dir, cache_dir):
    source_swift = os.path.join(template_dir, "main.swift")
    binary_path = os.path.join(template_dir, "WebAppBinary")
    
    # Check if binary exists and is newer than source
    if os.path.exists(binary_path):
        if os.path.getmtime(binary_path) >= os.path.getmtime(source_swift):
            return binary_path
            
    print("[*] Compiling native Swift wrapper engine...")
    os.makedirs(cache_dir, exist_ok=True)
    
    cmd = [
        "swiftc",
        "-O",
        "-target", "arm64-apple-macos12.0",
        "-module-cache-path", cache_dir,
        source_swift,
        "-o", binary_path
    ]
    subprocess.run(cmd, check=True)
    print(f"[+] Swift wrapper engine compiled successfully ({os.path.getsize(binary_path) // 1024} KB)")
    return binary_path

def build_application(
    name,
    url,
    icon=None,
    output_dir="./",
    bundle_id=None,
    user_agent=None,
    width=1200,
    height=800,
    min_width=400,
    min_height=300,
    title_bar_hidden=False,
    start_maximized=False,
    allow_external=True,
    custom_css=None,
    custom_js=None,
    install_to_apps=False
):
    clean_name = sanitize_name(name)
    if not clean_name:
        raise ValueError("App name is required and cannot be empty.")
    
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    if not bundle_id:
        bundle_id = create_bundle_id(clean_name)

    if install_to_apps:
        user_apps = os.path.expanduser("~/Applications")
        os.makedirs(user_apps, exist_ok=True)
        output_dir = user_apps

    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    app_bundle_path = os.path.join(output_dir, f"{clean_name}.app")
    if os.path.exists(app_bundle_path):
        print(f"[*] Overwriting existing application at {app_bundle_path}...")
        shutil.rmtree(app_bundle_path)

    contents_dir = os.path.join(app_bundle_path, "Contents")
    macos_dir = os.path.join(contents_dir, "MacOS")
    resources_dir = os.path.join(contents_dir, "Resources")
    os.makedirs(macos_dir, exist_ok=True)
    os.makedirs(resources_dir, exist_ok=True)

    template_dir = str(BASE_DIR / "src" / "template")
    cache_dir = str(BASE_DIR / ".cache" / "module-cache")
    binary_source = ensure_binary(template_dir, cache_dir)

    # 1. Copy Executable
    executable_name = clean_name.replace(" ", "")
    executable_dest = os.path.join(macos_dir, executable_name)
    shutil.copy2(binary_source, executable_dest)
    os.chmod(executable_dest, 0o755)

    # 2. Generate and copy Icon
    icon_dest = os.path.join(resources_dir, "AppIcon.icns")
    print(f"[*] Preparing application icon for '{clean_name}'...")
    generate_icon_for_app(url, clean_name, icon, icon_dest)

    # 3. Create Info.plist
    info_plist_template = os.path.join(template_dir, "Info.plist.template")
    with open(info_plist_template, "r", encoding="utf-8") as f:
        plist_content = f.read()

    plist_content = plist_content.replace("__APP_NAME__", clean_name)
    plist_content = plist_content.replace("__EXECUTABLE_NAME__", executable_name)
    plist_content = plist_content.replace("__BUNDLE_IDENTIFIER__", bundle_id)

    with open(os.path.join(contents_dir, "Info.plist"), "w", encoding="utf-8") as f:
        f.write(plist_content)

    # 4. Create config.json
    config_data = {
        "name": clean_name,
        "url": url,
        "bundleId": bundle_id,
        "userAgent": user_agent,
        "width": width,
        "height": height,
        "minWidth": min_width,
        "minHeight": min_height,
        "allowExternalLinksInDefaultBrowser": allow_external,
        "customCss": custom_css,
        "customJs": custom_js,
        "titleBarHidden": title_bar_hidden,
        "startMaximized": start_maximized
    }

    with open(os.path.join(resources_dir, "config.json"), "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2, ensure_ascii=False)

    # 5. Notify LaunchServices
    subprocess.run(["touch", app_bundle_path])

    app_size_mb = sum(
        os.path.getsize(os.path.join(dirpath, filename))
        for dirpath, _, filenames in os.walk(app_bundle_path)
        for filename in filenames
    ) / (1024 * 1024)

    print("\n" + "=" * 55)
    print(f"🎉  Success! Standalone Mac App created:")
    print(f"    App Name : {clean_name}")
    print(f"    Target   : {url}")
    print(f"    Bundle ID: {bundle_id}")
    print(f"    App Path : {app_bundle_path}")
    print(f"    App Size : {app_size_mb:.2f} MB (Ultra-lightweight!)")
    print("=" * 55 + "\n")

    return app_bundle_path

def main():
    parser = argparse.ArgumentParser(description="Convert any web application into a standalone lightweight macOS native app.")
    parser.add_argument("--name", "-n", required=True, help="Display Name of the App (e.g. 'Google NotebookLM')")
    parser.add_argument("--url", "-u", required=True, help="Starting URL of the Web App (e.g. 'https://notebooklm.google.com')")
    parser.add_argument("--icon", "-i", default=None, help="Path to custom image file for the app icon (PNG/JPEG/ICO/ICNS)")
    parser.add_argument("--output", "-o", default="./", help="Directory where .app bundle will be saved")
    parser.add_argument("--bundle-id", "-b", default=None, help="Custom bundle identifier (e.g. 'com.company.myapp')")
    parser.add_argument("--user-agent", default=None, help="Custom User-Agent string")
    parser.add_argument("--width", type=int, default=1200, help="Initial window width (default: 1200)")
    parser.add_argument("--height", type=int, default=800, help="Initial window height (default: 800)")
    parser.add_argument("--hidden-titlebar", action="store_true", help="Hide title bar for a modern borderless look")
    parser.add_argument("--maximized", action="store_true", help="Start window in maximized mode")
    parser.add_argument("--install", action="store_true", help="Install directly to ~/Applications")
    parser.add_argument("--custom-css", default=None, help="Custom CSS string to inject into the web page")
    parser.add_argument("--custom-js", default=None, help="Custom JavaScript to execute on page load")

    args = parser.parse_args()

    try:
        build_application(
            name=args.name,
            url=args.url,
            icon=args.icon,
            output_dir=args.output,
            bundle_id=args.bundle_id,
            user_agent=args.user_agent,
            width=args.width,
            height=args.height,
            title_bar_hidden=args.hidden_titlebar,
            start_maximized=args.maximized,
            install_to_apps=args.install,
            custom_css=args.custom_css,
            custom_js=args.custom_js
        )
    except Exception as e:
        print(f"[Error] Failed to build app: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
