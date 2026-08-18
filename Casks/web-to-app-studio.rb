cask "web-to-app-studio" do
  version "1.0.0"
  sha256 "a239deae883533d40a2dee07382e5599d7057c86519ef6bb20caddf1a2215e89"

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
