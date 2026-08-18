cask "web-to-app-studio" do
  version "1.0.1"
  sha256 "8766f5de15ae25badf5e41f0b0176b7fa6a77b126191dc6ba4cd30d1ce480549"

  url "https://github.com/nanonigit/web-to-app/releases/download/v#{version}/Web-to-App-Studio-v#{version}.zip"

  name "Web-to-App Studio"
  desc "Turn any web application into a standalone native macOS app powered by Chromium"
  homepage "https://github.com/nanonigit/web-to-app"

  app "Web-to-App Studio.app"

  postflight do
    system_command "/usr/bin/xattr",
                   args: ["-cr", "#{appdir}/Web-to-App Studio.app"],
                   sudo: false
  end
end
