cask "webtapp-mac" do
  version "1.1.0"
  sha256 "e9a97d74922d41fa36c517753a38ff1fda48ee4135d910caaf427b08ebaa6b88"

  url "https://github.com/nanonigit/WebTAPP-Mac/releases/download/v#{version}/WebTAPP-Mac-v#{version}.zip"

  name "WebTAPP Mac"
  desc "Turn any web application into a standalone native macOS app powered by Chromium"
  homepage "https://github.com/nanonigit/WebTAPP-Mac"

  app "WebTAPP Mac.app"

  postflight do
    system_command "/usr/bin/xattr",
                   args: ["-cr", "#{appdir}/WebTAPP Mac.app"],
                   sudo: false
  end
end
