# Web-to-App Studio (Chromium Powered)

[English](README.md) | [日本語](README.ja.md)

Google NotebookLMやFacebook Messenger、note、ChatGPT、Claude、NotionなどのWebサービスを、**わずか1〜2秒で独立したmacOSネイティブアプリ（`.app`）に変換する高速デスクトップツール**です。

Chromiumランタイム（Electronベース）を内蔵しており、Googleの埋め込みブラウザ遮断（Botguard）を回避してGoogleアカウントログイン（NotebookLM、Gmail、Google Drive等）に100%完全対応し、アプリごとの完全なセッション分離を提供します。

---

## ✨ 主な特徴

- 🚀 **1クリックで独立アプリ生成**: コマンドまたはGUIから約1〜2秒で `.app` を高速生成・配置。
- 🔑 **Google OAuth 100% 完全対応**: 本物のChromiumエンジンにより、Google Botguardの偽装検知を通過。「安全でないアプリ」警告なしでログイン可能。
- 🔒 **完全なセッション分離**: アプリごとに独立した `persist:appId` パーティションとデータ保存領域を割り当て。複数アカウントの使い分けも容易。
- 🎨 **高解像度アイコン自動取得**: WebサイトからApple Touch IconやManifest、Faviconを自動抽出し、macOSネイティブの `.icns` を生成。
- 🖥️ **macOS ネイティブ体験**:
  - macOS Dockの未読バッジカウント自動表示
  - 標準ショートカットキー（`Cmd+R`, `Cmd+W`, `Cmd+Q`, `Cmd+[`, `Cmd+]`, `Cmd++`, `Cmd+-`）
  - ウィンドウサイズ・位置の自動記憶
  - マイク・カメラ・通知パーミッション対応
  - モダンな枠なしタイトルバー（Full View）対応
- 📦 **GUIスタジオ ＋ CLI両対応**: 直感的な `Web-to-App Studio.app` またはターミナルコマンド `web-to-app` を利用可能。

---

## 📥 インストール方法

### Homebrew Cask 経由（推奨）

```bash
brew tap nanonigit/web-to-app
brew install --cask web-to-app-studio
```

### 手動ダウンロード

[Releases](https://github.com/nanonigit/web-to-app/releases) から最新の `.dmg` または `.zip` をダウンロードし、展開した **Web-to-App Studio.app** を `/Applications` または `~/Applications` フォルダに移動してください。

---

## 🚀 使い方

### 1. GUI スタジオで作成する（推奨）

1. Spotlight（`Cmd + Space`）またはLaunchpadから **Web-to-App Studio.app** を起動します。
2. プリセット（Google Notebook, Messenger, note, ChatGPT, Claude, Notion等）を選択するか、任意のURLを入力します。
3. （任意）「ファイル選択...」から好きなアイコン画像を指定するか、空欄にしてWebサイトから自動取得させます。
4. **「🚀 独立Macアプリ（.app）を作成」** をクリックします。
5. `~/Applications/` に即座にアプリが生成され、SpotlightやDockからすぐに起動できます。

---

### 2. コマンドライン（CLI）で作成する

```bash
# Google Notebook を作成して ~/Applications に配置
./bin/web-to-app --name "Google Notebook" --url "https://notebooklm.google.com" --install

# Messenger を作成
./bin/web-to-app --name "Messenger" --url "https://www.messenger.com" --install

# カスタムアイコンと枠なしウィンドウで作成
./bin/web-to-app --name "My App" --url "https://example.com" --icon ./icon.png --hidden-titlebar --install
```

#### CLI オプション一覧:

| オプション | 説明 |
| :--- | :--- |
| `--name`, `-n` | **[必須]** アプリの表示名 (例: `"Google Notebook"`) |
| `--url`, `-u` | **[必須]** 開始URL (例: `"https://notebooklm.google.com"`) |
| `--install` | `~/Applications/` に直接インストール |
| `--icon`, `-i` | カスタムアイコン画像（PNG/JPEG/ICNS）。省略時はURLから自動取得 |
| `--hidden-titlebar` | モダンな枠なしタイトルバー |
| `--width`, `--height` | 初期のウィンドウサイズ |
| `--output`, `-o` | 出力先ディレクトリ（デフォルト: カレントディレクトリ） |

---

## 🛠️ アーキテクチャ

```text
web-to-app/
├── bin/
│   └── web-to-app            # CLI実行スクリプト
├── src/
│   ├── studio/               # Web-to-App Studio GUI アプリケーション本体
│   │   ├── main.js
│   │   ├── preload.js
│   │   └── index.html
│   ├── template/             # Chromiumランタイムテンプレート
│   │   ├── main.js
│   │   ├── preload.js
│   │   └── package.json
│   └── generator/            # パッケージング & アイコン抽出エンジン
│       ├── build_app.py
│       ├── build_studio.py
│       └── icon_processor.py
└── Casks/                    # Homebrew Cask 定義ファイル
    └── web-to-app-studio.rb
```

---

## 📄 ライセンス

MIT License.
