#!/usr/bin/env node
/**
 * symbolicate.js — turn a minified browser stack into original file / line / function.
 *
 * Works for any bundler that emits source maps (Vite `build.sourcemap: 'hidden'`,
 * webpack `devtool: 'hidden-source-map'`, …). The maps MUST come from the same build
 * that produced the stack — match by the content hash in the bundle filename.
 *
 * Setup (once, in this folder):   npm install source-map
 *
 * Usage:
 *   node modules/log-triage/symbolicate.js --maps path/to/dist/assets --stack stack.txt
 *   node modules/log-triage/symbolicate.js --maps path/to/dist < stack.txt
 *   python modules/log-triage/triage_logs.py … --symbolicate-maps path/to/dist   (calls this)
 *
 * --maps is searched recursively for `<bundle>.js.map`. Non-frame lines pass through
 * unchanged; resolved frames keep the original minified location in brackets.
 */
const fs = require('fs');
const path = require('path');

let SourceMapConsumer;
try {
  ({ SourceMapConsumer } = require('source-map'));
} catch {
  console.error('Missing dependency. Run:  npm install source-map   (in modules/log-triage)');
  process.exit(1);
}

function arg(name) {
  const i = process.argv.indexOf(name);
  return i !== -1 && process.argv[i + 1] ? process.argv[i + 1] : null;
}

const mapsDir = arg('--maps');
const stackFile = arg('--stack');
if (!mapsDir) {
  console.error('Usage: node symbolicate.js --maps <dir> [--stack file]  (or pipe a stack on stdin)');
  process.exit(1);
}
const input = stackFile ? fs.readFileSync(stackFile, 'utf8') : fs.readFileSync(0, 'utf8');

// index every *.js.map under mapsDir by basename
const index = new Map();
(function walk(d) {
  for (const e of fs.readdirSync(d, { withFileTypes: true })) {
    const p = path.join(d, e.name);
    if (e.isDirectory()) { if (e.name !== 'node_modules') walk(p); }
    else if (e.name.endsWith('.js.map')) index.set(e.name.slice(0, -4), p);
  }
})(mapsDir);

const FRAME = /([A-Za-z0-9_.\-]+\.(?:m?js|cjs)):(\d+):(\d+)/;
const cache = new Map();
function loadMap(jsName) {
  if (cache.has(jsName)) return cache.get(jsName);
  const p = index.get(jsName);
  const raw = p ? JSON.parse(fs.readFileSync(p, 'utf8')) : null;
  cache.set(jsName, raw);
  return raw;
}

async function resolve(raw, line, col) {
  // V8 columns are 1-based; source-map wants 0-based. Try col-1, then col.
  return SourceMapConsumer.with(raw, null, (c) => {
    let o = c.originalPositionFor({ line, column: Math.max(col - 1, 0) });
    if (!o.source) o = c.originalPositionFor({ line, column: col });
    return o;
  });
}

(async () => {
  const out = [];
  let resolved = 0, missing = 0;
  for (const line of input.split(/\r?\n/)) {
    const m = line.match(FRAME);
    if (!m) { out.push(line); continue; }
    const [, jsName, ln, col] = m;
    const raw = loadMap(jsName);
    if (!raw) { missing++; out.push(`${line}    <no map for ${jsName} — wrong build?>`); continue; }
    const o = await resolve(raw, Number(ln), Number(col));
    if (o && o.source) {
      resolved++;
      out.push(`    at ${o.name || '?'} (${o.source}:${o.line}:${o.column})    [${jsName}:${ln}:${col}]`);
    } else {
      out.push(`${line}    <unresolved>`);
    }
  }
  console.log(out.join('\n'));
  if (missing) console.error(`symbolicate: ${resolved} frame(s) resolved, ${missing} without a matching map (maps must be from the deployed build)`);
})().catch((e) => { console.error('symbolicate error:', e.message); process.exit(1); });
