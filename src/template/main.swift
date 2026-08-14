import Cocoa
import WebKit
import CryptoKit

// MARK: - App Configuration
struct AppConfig: Codable {
    var name: String
    var url: String
    var bundleId: String
    var userAgent: String?
    var width: Double?
    var height: Double?
    var minWidth: Double?
    var minHeight: Double?
    var allowExternalLinksInDefaultBrowser: Bool?
    var customCss: String?
    var customJs: String?
    var titleBarHidden: Bool?
    var startMaximized: Bool?

    static func load() -> AppConfig {
        if let configURL = Bundle.main.url(forResource: "config", withExtension: "json"),
           let data = try? Data(contentsOf: configURL),
           let config = try? JSONDecoder().decode(AppConfig.self, from: data) {
            return config
        }
        return AppConfig(
            name: Bundle.main.object(forInfoDictionaryKey: "CFBundleName") as? String ?? "Web App",
            url: "https://google.com",
            bundleId: Bundle.main.bundleIdentifier ?? "com.webtoapp.generic",
            userAgent: nil,
            width: 1200,
            height: 800,
            minWidth: 400,
            minHeight: 300,
            allowExternalLinksInDefaultBrowser: true,
            customCss: nil,
            customJs: nil,
            titleBarHidden: false,
            startMaximized: false
        )
    }
}

// MARK: - UUID Helper for Isolated Storage
func deterministicUUID(from string: String) -> UUID {
    let hash = Insecure.MD5.hash(data: Data(string.utf8))
    var bytes = Array(hash)
    bytes[6] = (bytes[6] & 0x0F) | 0x30 // RFC 4122 version 3
    bytes[8] = (bytes[8] & 0x3F) | 0x80 // RFC 4122 variant
    let tuple: uuid_t = (
        bytes[0], bytes[1], bytes[2], bytes[3],
        bytes[4], bytes[5], bytes[6], bytes[7],
        bytes[8], bytes[9], bytes[10], bytes[11],
        bytes[12], bytes[13], bytes[14], bytes[15]
    )
    return UUID(uuid: tuple)
}

// MARK: - App Delegate
class AppDelegate: NSObject, NSApplicationDelegate, WKNavigationDelegate, WKUIDelegate {
    var window: NSWindow!
    var webView: WKWebView!
    var config: AppConfig!
    var initialHost: String = ""
    var titleObservation: NSKeyValueObservation?
    var popupWindows: [NSWindow] = []

    func applicationDidFinishLaunching(_ notification: Notification) {
        config = AppConfig.load()
        if let targetURL = URL(string: config.url) {
            initialHost = targetURL.host?.lowercased() ?? ""
        }

        setupMenuBar()
        setupMainWindow()
        loadWebContent()
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        return true
    }

    func applicationSupportsSecureRestorableState(_ app: NSApplication) -> Bool {
        return true
    }

    // MARK: - Window & WebView Setup
    func setupMainWindow() {
        let initialWidth = CGFloat(config.width ?? 1200)
        let initialHeight = CGFloat(config.height ?? 800)
        let screenRect = NSScreen.main?.visibleFrame ?? NSRect(x: 0, y: 0, width: 1440, height: 900)
        let originX = screenRect.origin.x + (screenRect.width - initialWidth) / 2
        let originY = screenRect.origin.y + (screenRect.height - initialHeight) / 2
        let windowRect = NSRect(x: originX, y: originY, width: initialWidth, height: initialHeight)

        var styleMask: NSWindow.StyleMask = [.titled, .closable, .miniaturizable, .resizable]
        if config.titleBarHidden == true {
            styleMask.insert(.fullSizeContentView)
        }

        window = NSWindow(contentRect: windowRect, styleMask: styleMask, backing: .buffered, defer: false)
        window.title = config.name
        window.minSize = NSSize(width: config.minWidth ?? 400, height: config.minHeight ?? 300)
        window.setFrameAutosaveName("MainWindow_\(config.bundleId)")
        window.isReleasedWhenClosed = false
        window.collectionBehavior = [.fullScreenPrimary, .managed]

        if config.titleBarHidden == true {
            window.titlebarAppearsTransparent = true
            window.titleVisibility = .hidden
        }

        // WebKit Configuration with Isolated Storage
        let webConfiguration = WKWebViewConfiguration()
        if #available(macOS 14.0, *) {
            let storeId = deterministicUUID(from: config.bundleId)
            webConfiguration.websiteDataStore = WKWebsiteDataStore(forIdentifier: storeId)
        } else {
            webConfiguration.websiteDataStore = WKWebsiteDataStore.default()
        }

        webConfiguration.preferences.isElementFullscreenEnabled = true
        webConfiguration.defaultWebpagePreferences.allowsContentJavaScript = true

        // User Agent: Default to modern Chrome User-Agent to prevent Google OAuth 403 blocks
        let chromeUA = config.userAgent ?? "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"

        webView = WKWebView(frame: window.contentView?.bounds ?? .zero, configuration: webConfiguration)
        webView.autoresizingMask = [.width, .height]
        webView.customUserAgent = chromeUA
        webView.allowsBackForwardNavigationGestures = true
        webView.navigationDelegate = self
        webView.uiDelegate = self

        // Observe Title for Window Title and Unread Badge updates
        titleObservation = webView.observe(\.title, options: [.new]) { [weak self] _, change in
            guard let self = self, let newTitle = change.newValue as? String, !newTitle.isEmpty else { return }
            self.window.title = newTitle
            self.updateDockBadge(from: newTitle)
        }

        window.contentView = webView
        window.makeKeyAndOrderFront(nil)

        if config.startMaximized == true {
            window.zoom(nil)
        }
    }

    func loadWebContent() {
        guard let url = URL(string: config.url) else { return }
        var request = URLRequest(url: url)
        request.cachePolicy = .useProtocolCachePolicy
        webView.load(request)
    }

    // MARK: - Dock Badge Parsing
    func updateDockBadge(from title: String) {
        let pattern = #"(?:\(|\[)(\d+\+?)(?:\)|\])"#
        if let regex = try? NSRegularExpression(pattern: pattern, options: []),
           let match = regex.firstMatch(in: title, options: [], range: NSRange(location: 0, length: title.utf16.count)) {
            if let range = Range(match.range(at: 1), in: title) {
                let countStr = String(title[range])
                NSApp.dockTile.badgeLabel = countStr
                return
            }
        }
        NSApp.dockTile.badgeLabel = nil
    }

    // MARK: - WKNavigationDelegate
    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        if let css = config.customCss, !css.isEmpty {
            let escapedCSS = css.replacingOccurrences(of: "\\", with: "\\\\")
                                .replacingOccurrences(of: "`", with: "\\`")
                                .replacingOccurrences(of: "\n", with: " ")
            let cssScript = """
            (function() {
                var style = document.createElement('style');
                style.type = 'text/css';
                style.innerHTML = `\(escapedCSS)`;
                document.head.appendChild(style);
            })();
            """
            webView.evaluateJavaScript(cssScript, completionHandler: nil)
        }

        if let js = config.customJs, !js.isEmpty {
            webView.evaluateJavaScript(js, completionHandler: nil)
        }
    }

    func webView(_ webView: WKWebView, decidePolicyFor navigationAction: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        guard let url = navigationAction.request.url else {
            decisionHandler(.allow)
            return
        }

        let scheme = url.scheme?.lowercased() ?? ""
        if scheme != "http" && scheme != "https" {
            NSWorkspace.shared.open(url)
            decisionHandler(.cancel)
            return
        }

        let targetHost = url.host?.lowercased() ?? ""

        // Check if authentication domain (OAuth flows)
        let authKeywords = [
            "accounts.google.com", "appleid.apple.com", "login.microsoftonline.com",
            "facebook.com", "github.com/login", "auth0.com", "okta.com", "clerk.com",
            "oauth", "login", "signin", "sso"
        ]
        let isAuthFlow = authKeywords.contains { targetHost.contains($0) || url.absoluteString.contains($0) }

        if navigationAction.navigationType == .linkActivated {
            let isSameHost = targetHost == initialHost || targetHost.hasSuffix("." + initialHost) || initialHost.hasSuffix("." + targetHost)

            if !isSameHost && !isAuthFlow && (config.allowExternalLinksInDefaultBrowser ?? true) {
                NSWorkspace.shared.open(url)
                decisionHandler(.cancel)
                return
            }
        }

        decisionHandler(.allow)
    }

    // MARK: - WKUIDelegate (Popups, OAuth & Media Permissions)
    func webView(_ webView: WKWebView, createWebViewWith configuration: WKWebViewConfiguration, for navigationAction: WKNavigationAction, windowFeatures: WKWindowFeatures) -> WKWebView? {
        let popupWidth = CGFloat(windowFeatures.width?.doubleValue ?? 600)
        let popupHeight = CGFloat(windowFeatures.height?.doubleValue ?? 700)
        let screenRect = NSScreen.main?.visibleFrame ?? NSRect(x: 0, y: 0, width: 1440, height: 900)
        let popupRect = NSRect(
            x: screenRect.origin.x + (screenRect.width - popupWidth) / 2,
            y: screenRect.origin.y + (screenRect.height - popupHeight) / 2,
            width: popupWidth,
            height: popupHeight
        )

        let popupWindow = NSWindow(
            contentRect: popupRect,
            styleMask: [.titled, .closable, .resizable],
            backing: .buffered,
            defer: false
        )
        popupWindow.title = "Login / Authorization"
        popupWindow.isReleasedWhenClosed = false

        let popupWebView = WKWebView(frame: popupWindow.contentView?.bounds ?? .zero, configuration: configuration)
        popupWebView.autoresizingMask = [.width, .height]
        popupWebView.customUserAgent = webView.customUserAgent
        popupWebView.uiDelegate = self
        popupWebView.navigationDelegate = self

        popupWindow.contentView = popupWebView
        popupWindow.makeKeyAndOrderFront(nil)
        popupWindows.append(popupWindow)

        return popupWebView
    }

    func webViewDidClose(_ webView: WKWebView) {
        if let window = webView.window {
            window.close()
            popupWindows.removeAll { $0 == window }
        }
    }

    @available(macOS 12.0, *)
    func webView(_ webView: WKWebView, requestMediaCapturePermissionFor origin: WKSecurityOrigin, initiatedByFrame frame: WKFrameInfo, type: WKMediaCaptureType, decisionHandler: @escaping (WKPermissionDecision) -> Void) {
        decisionHandler(.grant)
    }

    // MARK: - Actions
    @objc func reloadPage() {
        webView.reload()
    }

    @objc func forceReloadPage() {
        webView.reloadFromOrigin()
    }

    @objc func goBack() {
        if webView.canGoBack {
            webView.goBack()
        }
    }

    @objc func goForward() {
        if webView.canGoForward {
            webView.goForward()
        }
    }

    @objc func zoomIn() {
        webView.pageZoom += 0.1
    }

    @objc func zoomOut() {
        if webView.pageZoom > 0.3 {
            webView.pageZoom -= 0.1
        }
    }

    @objc func actualSize() {
        webView.pageZoom = 1.0
    }

    // MARK: - Menu Bar
    func setupMenuBar() {
        let mainMenu = NSMenu()

        // 1. App Menu
        let appMenuItem = NSMenuItem()
        let appMenu = NSMenu()
        let appName = config.name

        appMenu.addItem(NSMenuItem(title: "About \(appName)", action: #selector(NSApplication.orderFrontStandardAboutPanel(_:)), keyEquivalent: ""))
        appMenu.addItem(NSMenuItem.separator())
        appMenu.addItem(NSMenuItem(title: "Hide \(appName)", action: #selector(NSApplication.hide(_:)), keyEquivalent: "h"))
        let hideOthers = NSMenuItem(title: "Hide Others", action: #selector(NSApplication.hideOtherApplications(_:)), keyEquivalent: "h")
        hideOthers.keyEquivalentModifierMask = [.command, .option]
        appMenu.addItem(hideOthers)
        appMenu.addItem(NSMenuItem(title: "Show All", action: #selector(NSApplication.unhideAllApplications(_:)), keyEquivalent: ""))
        appMenu.addItem(NSMenuItem.separator())
        appMenu.addItem(NSMenuItem(title: "Quit \(appName)", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q"))
        appMenuItem.submenu = appMenu
        mainMenu.addItem(appMenuItem)

        // 2. Edit Menu (First Responder Actions for standard text editing)
        let editMenuItem = NSMenuItem()
        let editMenu = NSMenu(title: "Edit")
        editMenu.addItem(NSMenuItem(title: "Undo", action: #selector(UndoManager.undo), keyEquivalent: "z"))
        editMenu.addItem(NSMenuItem(title: "Redo", action: #selector(UndoManager.redo), keyEquivalent: "Z"))
        editMenu.addItem(NSMenuItem.separator())
        editMenu.addItem(NSMenuItem(title: "Cut", action: #selector(NSText.cut(_:)), keyEquivalent: "x"))
        editMenu.addItem(NSMenuItem(title: "Copy", action: #selector(NSText.copy(_:)), keyEquivalent: "c"))
        editMenu.addItem(NSMenuItem(title: "Paste", action: #selector(NSText.paste(_:)), keyEquivalent: "v"))
        editMenu.addItem(NSMenuItem(title: "Select All", action: #selector(NSText.selectAll(_:)), keyEquivalent: "a"))
        editMenuItem.submenu = editMenu
        mainMenu.addItem(editMenuItem)

        // 3. View Menu
        let viewMenuItem = NSMenuItem()
        let viewMenu = NSMenu(title: "View")
        viewMenu.addItem(NSMenuItem(title: "Reload", action: #selector(reloadPage), keyEquivalent: "r"))
        let forceReload = NSMenuItem(title: "Force Reload", action: #selector(forceReloadPage), keyEquivalent: "R")
        viewMenu.addItem(forceReload)
        viewMenu.addItem(NSMenuItem.separator())
        viewMenu.addItem(NSMenuItem(title: "Zoom In", action: #selector(zoomIn), keyEquivalent: "+"))
        viewMenu.addItem(NSMenuItem(title: "Zoom Out", action: #selector(zoomOut), keyEquivalent: "-"))
        viewMenu.addItem(NSMenuItem(title: "Actual Size", action: #selector(actualSize), keyEquivalent: "0"))
        viewMenu.addItem(NSMenuItem.separator())
        viewMenu.addItem(NSMenuItem(title: "Toggle Full Screen", action: #selector(NSWindow.toggleFullScreen(_:)), keyEquivalent: "f"))
        viewMenuItem.submenu = viewMenu
        mainMenu.addItem(viewMenuItem)

        // 4. History Menu
        let historyMenuItem = NSMenuItem()
        let historyMenu = NSMenu(title: "History")
        historyMenu.addItem(NSMenuItem(title: "Back", action: #selector(goBack), keyEquivalent: "["))
        historyMenu.addItem(NSMenuItem(title: "Forward", action: #selector(goForward), keyEquivalent: "]"))
        historyMenuItem.submenu = historyMenu
        mainMenu.addItem(historyMenuItem)

        // 5. Window Menu
        let windowMenuItem = NSMenuItem()
        let windowMenu = NSMenu(title: "Window")
        windowMenu.addItem(NSMenuItem(title: "Minimize", action: #selector(NSWindow.performMiniaturize(_:)), keyEquivalent: "m"))
        windowMenu.addItem(NSMenuItem(title: "Zoom", action: #selector(NSWindow.performZoom(_:)), keyEquivalent: ""))
        windowMenu.addItem(NSMenuItem.separator())
        windowMenu.addItem(NSMenuItem(title: "Close Window", action: #selector(NSWindow.performClose(_:)), keyEquivalent: "w"))
        windowMenuItem.submenu = windowMenu
        mainMenu.addItem(windowMenuItem)

        NSApp.mainMenu = mainMenu
    }
}

// MARK: - Application Entry Point
let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.regular)
app.activate(ignoringOtherApps: true)
app.run()
