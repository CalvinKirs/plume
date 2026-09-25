// Assembles a loadable extension for one browser target from the shared sources.
//
//   node scripts/build-extension.js chrome            -> dist/extension-chrome
//   node scripts/build-extension.js firefox --out DIR
//
// The shared code (src/, icons/) and the base manifest (manifest.json, which is the Chrome manifest)
// are common to every target. A target adds only what is specific to its browser, under
// targets/<name>/: a manifest.patch.json (an RFC 7396 JSON merge patch applied to the base manifest,
// where null removes a key) and any files the patched manifest points at.
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const ROOT = path.resolve(__dirname, '..');
const PATCH = 'manifest.patch.json';

// RFC 7396: objects merge, null deletes, anything else (arrays included) replaces.
function applyMergePatch(target, patch) {
  if (patch === null || typeof patch !== 'object' || Array.isArray(patch)) return patch;
  const out = target && typeof target === 'object' && !Array.isArray(target) ? { ...target } : {};
  for (const [key, value] of Object.entries(patch)) {
    if (value === null) delete out[key];
    else out[key] = applyMergePatch(out[key], value);
  }
  return out;
}

function listTargets(root = ROOT) {
  return fs.readdirSync(path.join(root, 'targets'), { withFileTypes: true })
    .filter((d) => d.isDirectory() && fs.existsSync(path.join(root, 'targets', d.name, PATCH)))
    .map((d) => d.name)
    .sort();
}

function buildManifest(target, root = ROOT) {
  const patchFile = path.join(root, 'targets', target, PATCH);
  if (!fs.existsSync(patchFile)) {
    throw new Error(`unknown target "${target}" (known: ${listTargets(root).join(', ')})`);
  }
  const base = JSON.parse(fs.readFileSync(path.join(root, 'manifest.json'), 'utf8'));
  return applyMergePatch(base, JSON.parse(fs.readFileSync(patchFile, 'utf8')));
}

function walk(dir, base = dir) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((d) => {
    const full = path.join(dir, d.name);
    return d.isDirectory() ? walk(full, base) : [path.relative(base, full)];
  });
}

// Files that go into the package, relative to the extension root: shared code and icons, plus the
// target's own files. Other targets' files and the patch itself stay out.
function packageFiles(target, root = ROOT) {
  const files = [...walk(path.join(root, 'src')).map((f) => path.join('src', f)),
    ...walk(path.join(root, 'icons')).map((f) => path.join('icons', f))];
  const own = path.join(root, 'targets', target);
  for (const f of walk(own)) if (f !== PATCH) files.push(path.join('targets', target, f));
  return files.sort();
}

// Every file the manifest refers to. A target must not point at something that is not packaged.
function referencedFiles(manifest) {
  const refs = [];
  const bg = manifest.background || {};
  if (bg.service_worker) refs.push(bg.service_worker);
  refs.push(...(bg.scripts || []));
  for (const cs of manifest.content_scripts || []) refs.push(...(cs.js || []), ...(cs.css || []));
  if (manifest.options_ui && manifest.options_ui.page) refs.push(manifest.options_ui.page);
  refs.push(...Object.values(manifest.icons || {}));
  return refs;
}

// The real path of p, even when p does not exist yet: symlinks in the part that exists are resolved.
function realish(p) {
  const resolved = path.resolve(p);
  if (fs.existsSync(resolved)) return fs.realpathSync(resolved);
  return path.join(realish(path.dirname(resolved)), path.basename(resolved));
}

const contains = (parent, child) => {
  const rel = path.relative(parent, child);
  return rel === '' || (!rel.startsWith('..') && !path.isAbsolute(rel));
};

// build() deletes the output directory before it writes, and the path comes from the command line, so
// it must not be able to name anything that matters: the filesystem root, the home directory, the
// current directory, the repository or anything inside the extension's own sources, or a directory
// that holds something other than an earlier build.
function assertSafeOutput(outDir, root = ROOT) {
  const out = realish(outDir);
  if (out === path.parse(out).root) throw new Error('refusing to use the filesystem root as the output directory');
  for (const [what, dir] of [['the extension sources', root], ['the current directory', process.cwd()], ['the home directory', os.homedir()]]) {
    const real = realish(dir);
    if (contains(out, real)) throw new Error(`refusing to replace ${out}: it contains ${what} (${real})`);
  }
  if (contains(realish(root), out)) throw new Error(`refusing to write inside the extension sources: ${out}`);
  if (fs.existsSync(out)) {
    const entries = fs.readdirSync(out);
    if (entries.length) {
      // Any browser extension has a root manifest.json, so its presence alone is no licence to delete.
      // Only a manifest carrying our own name counts as an earlier build of this extension.
      let name = null;
      try {
        name = JSON.parse(fs.readFileSync(path.join(out, 'manifest.json'), 'utf8')).name;
      } catch (e) { /* no manifest, or not JSON: not our build */ }
      const ours = JSON.parse(fs.readFileSync(path.join(root, 'manifest.json'), 'utf8')).name;
      if (name !== ours) {
        throw new Error(`refusing to replace ${out}: it is not empty and is not an earlier build of ${ours}`);
      }
    }
  }
}

function build(target, outDir, root = ROOT) {
  const manifest = buildManifest(target, root);
  assertSafeOutput(outDir, root);
  fs.rmSync(outDir, { recursive: true, force: true });
  fs.mkdirSync(outDir, { recursive: true });
  fs.writeFileSync(path.join(outDir, 'manifest.json'), JSON.stringify(manifest, null, 2) + '\n');
  for (const f of packageFiles(target, root)) {
    fs.mkdirSync(path.dirname(path.join(outDir, f)), { recursive: true });
    fs.copyFileSync(path.join(root, f), path.join(outDir, f));
  }
  const missing = referencedFiles(manifest).filter((f) => !fs.existsSync(path.join(outDir, f)));
  if (missing.length) throw new Error(`the ${target} manifest refers to files that are not packaged: ${missing.join(', ')}`);
  return { manifest, outDir };
}

module.exports = { assertSafeOutput, applyMergePatch, listTargets, buildManifest, packageFiles, referencedFiles, build };

if (require.main === module) {
  const args = process.argv.slice(2);
  const target = args[0];
  const at = args.indexOf('--out');
  if (!target) {
    console.error(`usage: build-extension.js <${listTargets().join('|')}> [--out DIR]`);
    process.exit(2);
  }
  if (at >= 0 && !args[at + 1]) {
    console.error('--out needs a directory');
    process.exit(2);
  }
  const outDir = path.resolve(at >= 0 ? args[at + 1] : path.join(ROOT, '..', 'dist', `extension-${target}`));
  try {
    build(target, outDir);
  } catch (e) {
    console.error(e.message);
    process.exit(1);
  }
  console.log(outDir);
}
