'use strict';
const fs = require('node:fs');
const path = require('node:path');
const { createHash } = require('node:crypto');

// Upstream Marquez serves static JS/CSS with max-age=14400 (4h). The HTML
// itself revalidates (max-age=0). Fingerprinting the URL prevents a visitor
// from continuing to run an older UI overlay after a new image rollout.
function fingerprintUrl(base, asset) {
  const bytes = fs.readFileSync(path.join(base, 'dist', asset));
  const digest = createHash('sha256').update(bytes).digest('hex').slice(0, 20);
  return '/' + asset + '?v=' + digest;
}

function install(base) {
  const file = path.join(base, 'dist/index.html');
  const source = fs.readFileSync(file, 'utf8');
  const bundle = /<script\b[^>]*src=["']\.\/bundle\.js["'][^>]*><\/script>/i;
  if (!bundle.test(source) || source.includes('public-readonly.js') || source.includes('public-datasets.js')) {
    throw Error('Unsupported or already patched Marquez HTML');
  }

  // Do not use immutable browser URLs for changing assets. Only our four
  // small static overlays are fingerprinted; native bundle.js stays upstream.
  const roCss = fingerprintUrl(base, 'public-readonly.css');
  const dsCss = fingerprintUrl(base, 'public-datasets.css');
  const roJs = fingerprintUrl(base, 'public-readonly.js');
  const dsJs = fingerprintUrl(base, 'public-datasets.js');
  const patched = source.replace(/<\/head>/i,
    '<link rel="stylesheet" href="' + roCss + '">\n' +
    '<link rel="stylesheet" href="' + dsCss + '">\n</head>')
    .replace(bundle, '<script src="' + roJs + '"></script>\n' +
      '<script src="' + dsJs + '"></script>\n$&');
  fs.writeFileSync(file, patched);
  return patched;
}
if (require.main === module) install(process.cwd());
module.exports = { install, fingerprintUrl };
