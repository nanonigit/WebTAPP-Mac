# Web-to-App: 超軽量 Webアプリ独立化ジェネレーター (WebCatalog for Mac)

Google NotebookLMやFacebook Messenger、ChatGPT、Claude、NotionなどのWebサービスを、**わずか0.2MB〜数MBの超軽量・高速な独立macOSネイティブアプリ（`.app`）** に変換するツールです。

---

## 🌟 主な特徴

- 🚀 **超軽量・超高速**: Electron（150MB〜）を一切使わず、macOS標準の **Swift + WKWebView (AppKit)** を採用。アプリサイズはわずか **0.2MB**。
- 🔒 **完全なセッション分離**: 各アプリ固有のBundle Identifierごとに独立した `WKWebsiteDataStore` を生成。アカウントの使い分けやクッキーの競合が起きません。
- 🔑 **Google / Meta ログイン完全対応**: Google等のOAuth認証ブロック（`403 disallowed_useragent`）を回避する最新デスクトップChrome User-Agentを自動設定。
- 🧭 **賢い外部リンク振り分け**: サービス内部の遷移やOAuth認証はアプリ内で処理し、外部サイトへのリンクはmacOS標準ブラウザ（Safari/Chrome）で開きます。
- 🎨 **アイコン自動取得 & `.icns` 変換**: Webサイトから高解像度のアイコンを自動抽出し、macOSネイティブの `.icns` を自動生成。
- ⌨️ **macOSネイティブ操作感**:
  - `Cmd + R` (リロード), `Cmd + Shift + R` (強制リロード)
  - `Cmd + [` / `Cmd + ]` (戻る / 進む)
  - `Cmd + +` / `Cmd + -` / `Cmd + 0` (ズームイン / ズームアウト / 標準サイズ)
  - `Cmd + W` (ウィンドウを閉じる), `Cmd + Q` (終了)
  - トラックパッドの2本指スワイプナビゲーション
  - Dockバッジ（未読通知数の自動表示）
  - カメラ・マイクのパーミッション自動付与（ビデオ通話対応）

---

## 🚀 使い方

### 1. GUI 画面で作成する（推奨）

ブラウザから直感的にアプリを作成できるGUIスタジオが付属しています：

```bash
/Users/naoki/.gemini/antigravity/scratch/web-to-app/bin/web-to-app-gui
```
ブラウザが開き、NotebookLMやMessengerのクイックプリセットからワンクリックでアプリを作成・インストールできます。

---

### 2. コマンドライン（CLI）で作成する

`web-to-app` コマンドで簡単に `.app` を生成できます。

#### 基本コマンド例:

```bash
# Google NotebookLM を作成して ~/Applications にインストール
/Users/naoki/.gemini/antigravity/scratch/web-to-app/bin/web-to-app \
  --name "Google NotebookLM" \
  --url "https://notebooklm.google.com" \
  --install

# Facebook Messenger を作成
/Users/naoki/.gemini/antigravity/scratch/web-to-app/bin/web-to-app \
  --name "Facebook Messenger" \
  --url "https://www.messenger.com" \
  --install

# ChatGPT をモダンな枠なしウィンドウ（Full View）で作成
/Users/naoki/.gemini/antigravity/scratch/web-to-app/bin/web-to-app \
  --name "ChatGPT" \
  --url "https://chatgpt.com" \
  --hidden-titlebar \
  --install
```

#### 利用可能なオプション:

| オプション | 説明 |
| :--- | :--- |
| `--name`, `-n` | **[必須]** アプリ名 (例: `"Google NotebookLM"`) |
| `--url`, `-u` | **[必須]** 開始URL (例: `"https://notebooklm.google.com"`) |
| `--install` | `~/Applications` に直接保存（SpotlightやLaunchpadから即起動可能） |
| `--output`, `-o` | `.app` を出力するディレクトリ（デフォルト: カレントディレクトリ） |
| `--icon`, `-i` | カスタムアイコン画像（PNG/JPEG/ICO/ICNS）。省略時はWebから自動取得 |
| `--hidden-titlebar` | モダンな枠なしタイトルバー（コンテンツ領域をウィンドウ上端まで拡大） |
| `--width` | 初期のウィンドウ幅 (デフォルト: `1200`) |
| `--height` | 初期のウィンドウ高さ (デフォルト: `800`) |
| `--bundle-id`, `-b` | カスタムBundle ID (デフォルト: `com.webtoapp.<name>`) |
| `--custom-css` | ページロード時に注入するカスタムCSS |
| `--custom-js` | ページロード時に実行するカスタムJavaScript |

---

## 📂 ディレクトリ構成

```text
web-to-app/
├── bin/
│   ├── web-to-app           # CLI実行スクリプト
│   └── web-to-app-gui       # GUIスタジオ起動スクリプト
├── src/
│   ├── template/            # Swift + AppKit + WKWebView テンプレート
│   │   ├── main.swift
│   │   ├── Info.plist.template
│   │   └── WebAppBinary     # 高速コンパイル済みネイティブバイナリ (~150KB)
│   ├── generator/           # アプリ組み立て & アイコン処理エンジン
│   │   ├── build_app.py
│   │   └── icon_processor.py
│   └── gui/                 # Web-to-App Studio (ローカルWeb GUI)
│       ├── server.py
│       └── index.html
└── dist/                    # 生成されたテスト用 .app バンドル
```
