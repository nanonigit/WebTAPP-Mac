#!/usr/bin/env python3
import os
import sys
import re
import json
import shutil
import argparse
import subprocess
import plistlib
from pathlib import Path

# Add current generator directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from icon_processor import generate_icon_for_app, convert_image_to_icns

def sanitize_name(name):
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

def create_bundle_id(name):
    slug = re.sub(r'[^a-zA-Z0-9]', '', name).lower()
    return f"com.webtoapp.{slug}"

def get_template_dir():
    candidates = [
        Path(__file__).resolve().parent.parent / "template",
        Path(__file__).resolve().parent.parent.parent / "src" / "template",
    ]
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]

def get_electron_base_app():
    candidates = [
        Path(__file__).resolve().parent.parent / "electron-base" / "Electron.app",
        Path(__file__).resolve().parent.parent.parent / "node_modules" / "electron" / "dist" / "Electron.app",
        Path(__file__).resolve().parent.parent / "node_modules" / "electron" / "dist" / "Electron.app"
    ]
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError(f"Electron base app not found. Checked: {[str(x) for x in candidates]}")

def build_application(
    name,
    url,
    icon=None,
    icon_preset=None,
    output_dir="./",
    bundle_id=None,
    user_agent=None,
    width=780,
    height=923,
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
        raise ValueError("App name is required.")
    
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    if not bundle_id:
        bundle_id = create_bundle_id(clean_name)

    if install_to_apps:
        user_apps = "/Applications"
        os.makedirs(user_apps, exist_ok=True)
        output_dir = user_apps

    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    app_bundle_path = os.path.join(output_dir, f"{clean_name}.app")
    if os.path.exists(app_bundle_path):
        print(f"[*] Overwriting existing application at {app_bundle_path}...")
        shutil.rmtree(app_bundle_path)

    # 1. Clone Electron.app base
    electron_base = get_electron_base_app()
    print(f"[*] Packaging standalone Chromium runtime for '{clean_name}'...")
    shutil.copytree(str(electron_base), app_bundle_path, symlinks=True)

    contents_dir = os.path.join(app_bundle_path, "Contents")
    macos_dir = os.path.join(contents_dir, "MacOS")
    resources_dir = os.path.join(contents_dir, "Resources")

    # 2. Rename Executable
    executable_name = clean_name.replace(" ", "")
    orig_exec = os.path.join(macos_dir, "Electron")
    dest_exec = os.path.join(macos_dir, executable_name)
    if os.path.exists(orig_exec):
        os.rename(orig_exec, dest_exec)

    # 3. Create Resources/app/ directory and copy runtime scripts
    app_pkg_dir = os.path.join(resources_dir, "app")
    os.makedirs(app_pkg_dir, exist_ok=True)

    template_dir = get_template_dir()
    shutil.copy2(str(template_dir / "package.json"), os.path.join(app_pkg_dir, "package.json"))
    shutil.copy2(str(template_dir / "main.js"), os.path.join(app_pkg_dir, "main.js"))
    shutil.copy2(str(template_dir / "preload.js"), os.path.join(app_pkg_dir, "preload.js"))

    # 4. Write config.json
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

    with open(os.path.join(app_pkg_dir, "config.json"), "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2, ensure_ascii=False)

    # 5. Generate and replace AppIcon.icns
    icon_dest = os.path.join(resources_dir, "AppIcon.icns")
    print(f"[*] Preparing application icon for '{clean_name}'...")
    generate_icon_for_app(url, clean_name, icon, icon_dest, icon_preset=icon_preset)
    
    # Also replace electron.icns
    electron_icns = os.path.join(resources_dir, "electron.icns")
    if os.path.exists(icon_dest):
        shutil.copy2(icon_dest, electron_icns)

    # 6. Update Info.plist
    info_plist_path = os.path.join(contents_dir, "Info.plist")
    with open(info_plist_path, "rb") as f:
        plist_data = plistlib.load(f)

    plist_data["CFBundleName"] = clean_name
    plist_data["CFBundleDisplayName"] = clean_name
    plist_data["CFBundleIdentifier"] = bundle_id
    plist_data["CFBundleExecutable"] = executable_name
    plist_data["CFBundleIconFile"] = "AppIcon.icns"
    plist_data["NSCameraUsageDescription"] = "This app requires access to the camera for video features."
    plist_data["NSMicrophoneUsageDescription"] = "This app requires access to the microphone for audio features."

    with open(info_plist_path, "wb") as f:
        plistlib.dump(plist_data, f)

    # 7. Notify LaunchServices
    subprocess.run(["touch", app_bundle_path])

    app_size_mb = sum(
        os.path.getsize(os.path.join(dirpath, filename))
        for dirpath, _, filenames in os.walk(app_bundle_path)
        for filename in filenames
        if not os.path.islink(os.path.join(dirpath, filename))
    ) / (1024 * 1024)

    print("\n" + "=" * 60)
    print(f"🎉  Success! Standalone Mac App created (Chromium Powered):")
    print(f"    App Name : {clean_name}")
    print(f"    Target   : {url}")
    print(f"    Bundle ID: {bundle_id}")
    print(f"    App Path : {app_bundle_path}")
    print(f"    Engine   : Chromium (Full Google OAuth / NotebookLM Support)")
    print(f"    App Size : {app_size_mb:.1f} MB")
    print("=" * 60 + "\n")

    return app_bundle_path

def main():
    parser = argparse.ArgumentParser(description="Convert any web application into a standalone macOS native app powered by Chromium.")
    parser.add_argument("--name", "-n", required=True, help="Display Name of the App (e.g. 'Google NotebookLM')")
    parser.add_argument("--url", "-u", required=True, help="Starting URL of the Web App (e.g. 'https://notebooklm.google.com')")
    parser.add_argument("--icon", "-i", default=None, help="Path to custom image file for the app icon (PNG/JPEG/ICO/ICNS)")
    parser.add_argument("--icon-preset", default=None, help="Functional category icon preset (ai, chat, docs, media, dev, analytics, shop, web)")
    parser.add_argument("--output", "-o", default="./", help="Directory where .app bundle will be saved")
    parser.add_argument("--bundle-id", "-b", default=None, help="Custom bundle identifier (e.g. 'com.company.myapp')")
    parser.add_argument("--user-agent", default=None, help="Custom User-Agent string")
    parser.add_argument("--width", type=int, default=780, help="Initial window width (default: 780)")
    parser.add_argument("--height", type=int, default=923, help="Initial window height (default: 923)")
    parser.add_argument("--hidden-titlebar", action="store_true", help="Hide title bar for a modern borderless look")
    parser.add_argument("--maximized", action="store_true", help="Start window in maximized mode")
    parser.add_argument("--install", action="store_true", help="Install directly to /Applications")
    parser.add_argument("--custom-css", default=None, help="Custom CSS string to inject into the web page")
    parser.add_argument("--custom-js", default=None, help="Custom JavaScript to execute on page load")

    args = parser.parse_args()

    try:
        build_application(
            name=args.name,
            url=args.url,
            icon=args.icon,
            icon_preset=args.icon_preset,
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
