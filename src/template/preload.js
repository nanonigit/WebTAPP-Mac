const path = require('path');
const fs = require('fs');

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
});
