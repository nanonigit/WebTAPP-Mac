#!/usr/bin/env python3
import os
import sys
import json
import shutil
import subprocess
import plistlib
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR / "src" / "generator"))
from icon_processor import convert_image_to_icns

def get_git_metadata():
    try:
        commit_count = subprocess.check_output(
            ["git", "-C", str(BASE_DIR), "rev-list", "--count", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()
    except Exception:
        commit_count = "1"

    try:
        short_sha = subprocess.check_output(
            ["git", "-C", str(BASE_DIR), "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()
    except Exception:
        short_sha = "dev"

    return f"1.1.{commit_count}", short_sha

def build_studio_app(output_dir=None):
    if not output_dir:
        output_dir = os.path.expanduser("~/Applications")
    
    os.makedirs(output_dir, exist_ok=True)
    app_name = "WebTAPP Mac"
    app_bundle_path = os.path.join(output_dir, f"{app_name}.app")
    
    electron_base = BASE_DIR / "node_modules" / "electron" / "dist" / "Electron.app"
    if not electron_base.exists():
        raise FileNotFoundError(f"Electron base app not found at {electron_base}")

    if os.path.exists(app_bundle_path):
        print(f"[*] Overwriting existing application at {app_bundle_path}...")
        shutil.rmtree(app_bundle_path)

    print(f"[*] Packaging {app_name} into {app_bundle_path}...")
    shutil.copytree(str(electron_base), app_bundle_path, symlinks=True)

    contents_dir = os.path.join(app_bundle_path, "Contents")
    macos_dir = os.path.join(contents_dir, "MacOS")
    resources_dir = os.path.join(contents_dir, "Resources")

    # Rename Executable
    exec_name = "WebTAPPMac"
    orig_exec = os.path.join(macos_dir, "Electron")
    dest_exec = os.path.join(macos_dir, exec_name)
    if os.path.exists(orig_exec):
        os.rename(orig_exec, dest_exec)

    # Copy Studio source to Resources/app/
    app_pkg_dir = os.path.join(resources_dir, "app")
    studio_src = BASE_DIR / "src" / "studio"
    shutil.copytree(str(studio_src), app_pkg_dir)

    # Write build_info.json into Resources/app/ for version & self-update verification
    app_version, git_sha = get_git_metadata()
    build_info = {
        "version": app_version,
        "gitSha": git_sha,
        "repoPath": str(BASE_DIR)
    }
    with open(os.path.join(app_pkg_dir, "build_info.json"), "w", encoding="utf-8") as bf:
        json.dump(build_info, bf, indent=2)

    # Copy generator & template & electron-base into app bundle for complete standalone self-containment
    shutil.copytree(str(BASE_DIR / "src" / "generator"), os.path.join(app_pkg_dir, "generator"))
    shutil.copytree(str(BASE_DIR / "src" / "template"), os.path.join(app_pkg_dir, "template"))
    
    updater_sh = os.path.join(app_pkg_dir, "generator", "update_mac_app.sh")
    if os.path.exists(updater_sh):
        os.chmod(updater_sh, 0o755)
        shutil.copy2(updater_sh, os.path.join(resources_dir, "update_mac_app.sh"))

    electron_base_dest = os.path.join(app_pkg_dir, "electron-base", "Electron.app")
    os.makedirs(os.path.dirname(electron_base_dest), exist_ok=True)
    shutil.copytree(str(electron_base), electron_base_dest, symlinks=True)

    # Generate and copy Icon
    icon_source = str(BASE_DIR / "studio_icon.png")
    icon_dest = os.path.join(resources_dir, "AppIcon.icns")
    convert_image_to_icns(icon_source, icon_dest, app_name, normalize_squircle=False)
    
    electron_icns = os.path.join(resources_dir, "electron.icns")
    if os.path.exists(icon_dest):
        shutil.copy2(icon_dest, electron_icns)

    # Update Info.plist
    info_plist_path = os.path.join(contents_dir, "Info.plist")
    with open(info_plist_path, "rb") as f:
        plist_data = plistlib.load(f)

    plist_data["CFBundleName"] = app_name
    plist_data["CFBundleDisplayName"] = app_name
    plist_data["CFBundleIdentifier"] = "com.webtapp.mac"
    plist_data["CFBundleExecutable"] = exec_name
    plist_data["CFBundleIconFile"] = "AppIcon.icns"
    plist_data["CFBundleShortVersionString"] = app_version
    plist_data["CFBundleVersion"] = git_sha

    with open(info_plist_path, "wb") as f:
        plistlib.dump(plist_data, f)

    # Ad-hoc code sign to ensure macOS Gatekeeper approval
    subprocess.run(["xattr", "-cr", app_bundle_path])
    subprocess.run(["codesign", "--force", "--deep", "--sign", "-", app_bundle_path])
    subprocess.run(["touch", app_bundle_path])

    print("\n" + "=" * 60)
    print(f"🎉  Success! Self-contained {app_name}.app generated successfully:")
    print(f"    Version  : v{app_version} ({git_sha})")
    print(f"    App Path : {app_bundle_path}")
    print("=" * 60 + "\n")
    return app_bundle_path

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else None
    build_studio_app(out)
