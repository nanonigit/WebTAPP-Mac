cask "webtapp-mac" do
  version "1.0.2"
  sha256 "9b8f56ae04d695d12d18ee1c88a9a7eb8d376a0667888c8b696f7f4cc1027c55"

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
