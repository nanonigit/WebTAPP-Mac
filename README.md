# Web-to-App Studio (Chromium Powered)

[English](README.md) | [日本語](README.ja.md)

An ultra-fast, lightweight macOS desktop application that turns any web service (Google Notebook, Facebook Messenger, note, ChatGPT, Claude, Notion, etc.) into a standalone macOS native app (`.app`).

Powered by an embedded Chromium runtime (Electron), providing 100% full compatibility with Google OAuth logins (NotebookLM, Gmail, Google Drive) and complete session isolation.

---

## ✨ Features

- 🚀 **1-Click Native App Generator**: Create standalone macOS applications in less than 2 seconds.
- 🔑 **100% Google OAuth & Passkey Compatibility**: Genuine Chromium engine passes Google's Botguard verification with zero warnings.
- 🔒 **Complete Session Isolation**: Each app uses its own persistent partition (`persist:appId`) and storage sandbox—run multiple isolated accounts effortlessly.
- 🎨 **Smart High-Resolution Icon Extraction**: Automatically extracts Apple Touch Icons, Manifest icons, and Favicons from web pages and compiles them into macOS `.icns`.
- 🖥️ **Native macOS Experience**:
  - Unread badge counter in macOS Dock
  - Standard macOS shortcuts (`Cmd+R`, `Cmd+W`, `Cmd+Q`, `Cmd+[`, `Cmd+]`, `Cmd++`, `Cmd+-`)
  - Auto window state restoration
  - Camera, microphone, and notification permission support
  - Optional frameless / borderless modern title bar (Full View)
- 📦 **Standalone Studio GUI + CLI**: Use either the sleek `Web-to-App Studio.app` GUI or the terminal CLI `web-to-app`.

---

## 📥 Installation

### Via Homebrew Cask

```bash
brew tap nanonigit/cocolite
brew install --cask web-to-app-studio
```

### Manual Download

Download the latest `.dmg` or `.zip` from [Releases](https://github.com/nanonigit/web-to-app/releases), open it, and move **Web-to-App Studio.app** to your `/Applications` or `~/Applications` folder.

---

## 🚀 Usage

### 1. Using the GUI Studio (Recommended)

1. Launch **Web-to-App Studio.app** from Spotlight (`Cmd + Space`) or Launchpad.
2. Pick a quick preset (Google Notebook, Messenger, note, ChatGPT, Claude, Notion, etc.) or enter a custom URL.
3. (Optional) Choose a custom icon image or let it auto-extract from the website.
4. Click **"🚀 独立Macアプリ（.app）を作成"** (Build Standalone App).
5. The generated app is instantly installed to `~/Applications/` and ready to launch!

---

### 2. Using the CLI

```bash
# Create Google Notebook and install to ~/Applications
./bin/web-to-app --name "Google Notebook" --url "https://notebooklm.google.com" --install

# Create Messenger
./bin/web-to-app --name "Messenger" --url "https://www.messenger.com" --install

# Create custom app with custom icon and frameless window
./bin/web-to-app --name "My App" --url "https://example.com" --icon ./icon.png --hidden-titlebar --install
```

#### CLI Options:

| Option | Description |
| :--- | :--- |
| `--name`, `-n` | **[Required]** Display Name of the app |
| `--url`, `-u` | **[Required]** Starting URL |
| `--install` | Directly install to `~/Applications/` |
| `--icon`, `-i` | Custom icon path (PNG/JPEG/ICNS). Omit to auto-extract from URL |
| `--hidden-titlebar` | Frameless modern title bar |
| `--width`, `--height` | Initial window dimensions |
| `--output`, `-o` | Output directory (defaults to current directory) |

---

## 🛠️ Architecture

```text
web-to-app/
├── bin/
│   └── web-to-app            # CLI executable
├── src/
│   ├── studio/               # Web-to-App Studio GUI Application
│   │   ├── main.js
│   │   ├── preload.js
│   │   └── index.html
│   ├── template/             # Chromium runtime template
│   │   ├── main.js
│   │   ├── preload.js
│   │   └── package.json
│   └── generator/            # Packaging & Icon Processor
│       ├── build_app.py
│       ├── build_studio.py
│       └── icon_processor.py
└── Casks/                    # Homebrew Cask Formula
    └── web-to-app-studio.rb
```

---

## 📄 License

MIT License.
