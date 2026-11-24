const path = require('path');
const fs = require('fs');
const { ipcRenderer } = require('electron');

function isTransparentColor(bg) {
  if (!bg || bg === 'transparent') return true;
  const m = bg.match(/rgba?\(\s*\d+\s*,\s*\d+\s*,\s*\d+(?:\s*,\s*([0-9.]+))?\s*\)/);
  if (m && m[1] !== undefined && parseFloat(m[1]) === 0) return true;
  return false;
}

function detectTopEdgeBackground() {
  try {
    const candidates = [
      document.elementFromPoint(Math.min(window.innerWidth - 20, 200), 12),
      document.querySelector('header, nav, [role="banner"]'),
      document.body,
      document.documentElement
    ];
    for (const el of candidates) {
      if (!el) continue;
      const bg = getComputedStyle(el).backgroundColor;
      if (!isTransparentColor(bg)) {
        return bg;
      }
    }
  } catch (e) {}
  return null;
}

function syncTitlebarTheme() {
  const bg = detectTopEdgeBackground();
  if (bg) {
    ipcRenderer.send('sync-titlebar-bg', bg);
  }
}

window.addEventListener('DOMContentLoaded', () => {
  try {
    const configPath = path.join(__dirname, 'config.json');
    if (fs.existsSync(configPath)) {
      const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
      if (config.customCss) {
        const style = document.createElement('style');
        style.type = 'text/css';
        style.innerHTML = config.customCss;
        document.head.appendChild(style);
      }
      if (config.customJs) {
        eval(config.customJs);
      }
    }
  } catch (e) {}

  syncTitlebarTheme();
  setTimeout(syncTitlebarTheme, 500);
  setTimeout(syncTitlebarTheme, 1800);
  if (typeof MutationObserver !== 'undefined' && document.documentElement) {
    let timer = null;
    const obs = new MutationObserver(() => {
      if (timer) clearTimeout(timer);
      timer = setTimeout(syncTitlebarTheme, 250);
    });
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ['class', 'data-theme', 'style'] });
  }
});
