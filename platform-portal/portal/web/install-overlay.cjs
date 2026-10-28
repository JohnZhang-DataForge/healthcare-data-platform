'use strict';
const fs = require('node:fs');
const path = require('node:path');
function install(base) {
  const file = path.join(base, 'dist/index.html');
  const source = fs.readFileSync(file, 'utf8');
  const bundle = /<script\b[^>]*src=["']\.\/bundle\.js["'][^>]*><\/script>/i;
  if (!bundle.test(source) || source.includes('public-readonly.js') || source.includes('public-datasets.js')) {
    throw Error('Unsupported or already patched Marquez HTML');
  }
  const patched = source.replace(/<\/head>/i,
    '<link rel="stylesheet" href="/public-readonly.css">\n' +
    '<link rel="stylesheet" href="/public-datasets.css">\n</head>')
    .replace(bundle, '<script src="/public-readonly.js"></script>\n' +
      '<script src="/public-datasets.js"></script>\n$&');
  fs.writeFileSync(file, patched);
  return patched;
}
if (require.main === module) install(process.cwd());
module.exports = { install };
