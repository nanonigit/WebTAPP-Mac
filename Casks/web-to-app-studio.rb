cask "web-to-app-studio" do
  version "1.0.0"
  sha256 "f28e0fb25b466d6380879abc986d38df149c8fa3ef7a3f44d50f5a8cc15dd804"

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
