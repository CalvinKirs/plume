const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { assertSafeOutput, applyMergePatch, listTargets, buildManifest, packageFiles, referencedFiles, build } = require('../scripts/build-extension');

const ROOT = path.resolve(__dirname, '..');
const source = JSON.parse(fs.readFileSync(path.join(ROOT, 'manifest.json'), 'utf8'));
const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), 'plume-build-'));

test('merge patch: objects merge, null removes, arrays and scalars replace', () => {
  const base = { a: 1, b: { c: 2, d: 3 }, e: [1, 2], f: 'x' };
  const patch = { a: null, b: { c: null, z: 9 }, e: [7], f: 'y', g: { h: 1 } };
  assert.deepStrictEqual(applyMergePatch(base, patch), { b: { d: 3, z: 9 }, e: [7], f: 'y', g: { h: 1 } });
  assert.deepStrictEqual(base.b, { c: 2, d: 3 }, 'the input is not modified');
  assert.deepStrictEqual(applyMergePatch({ a: 1 }, {}), { a: 1 });
});

test('the known targets are chrome and firefox, and an unknown one is refused', () => {
  assert.deepStrictEqual(listTargets(), ['chrome', 'firefox']);
  assert.throws(() => buildManifest('safari'), /unknown target "safari" \(known: chrome, firefox\)/);
});

test('Chrome: the built manifest is the source manifest, so the Chrome package cannot drift from it', () => {
  assert.deepStrictEqual(buildManifest('chrome'), source);
});

test('the source (Chrome) manifest carries nothing that belongs to Firefox', () => {
  assert.ok(!('browser_specific_settings' in source));
  assert.ok(!('scripts' in source.background));
  assert.strictEqual(source.background.service_worker, 'targets/chrome/service-worker.js');
});

test('Firefox differs from Chrome in exactly the keys that have to differ', () => {
  const ff = buildManifest('firefox');
  const differing = [...new Set([...Object.keys(source), ...Object.keys(ff)])]
    .filter((k) => JSON.stringify(source[k]) !== JSON.stringify(ff[k])).sort();
  assert.deepStrictEqual(differing, ['background', 'browser_specific_settings', 'key', 'version_name']);
  for (const k of ['manifest_version', 'name', 'version', 'permissions', 'host_permissions', 'content_scripts', 'options_ui', 'icons']) {
    assert.deepStrictEqual(ff[k], source[k], `${k} must be shared`);
  }
});

test('Firefox: an event page whose scripts load the platform layer first and the background core last', () => {
  const ff = buildManifest('firefox');
  assert.ok(!('service_worker' in ff.background), 'Firefox has no service workers');
  assert.strictEqual(ff.background.scripts[0], 'src/platform.js');
  assert.strictEqual(ff.background.scripts.at(-1), 'src/background.js');
  assert.match(ff.browser_specific_settings.gecko.id, /^[^@\s]+@[^@\s]+$/, 'an add-on id in email form');
});

test('the Chrome service worker loads the same scripts, in the same order, as the Firefox event page', () => {
  const bootstrap = fs.readFileSync(path.join(ROOT, 'targets', 'chrome', 'service-worker.js'), 'utf8');
  const chromeScripts = [...bootstrap.matchAll(/'\.\.\/\.\.\/(src\/[^']+)'/g)].map((m) => m[1]);
  assert.deepStrictEqual(chromeScripts, buildManifest('firefox').background.scripts);
});

test('every file a target refers to is packaged, and no target ships another target\'s files', () => {
  for (const target of listTargets()) {
    const { manifest, outDir } = build(target, path.join(tmp(), target));
    for (const f of referencedFiles(manifest)) assert.ok(fs.existsSync(path.join(outDir, f)), `${target}: ${f}`);
    const shipped = packageFiles(target);
    for (const other of listTargets().filter((t) => t !== target)) {
      assert.ok(!shipped.some((f) => f.startsWith(path.join('targets', other))), `${target} ships ${other} files`);
    }
    assert.ok(!shipped.some((f) => f.endsWith('manifest.patch.json')), 'the patch is a build input, not part of the package');
  }
});

test('a target that points at a file it does not ship fails the build', () => {
  const root = tmp();
  for (const d of ['src', 'icons', 'targets/x']) fs.mkdirSync(path.join(root, d), { recursive: true });
  fs.writeFileSync(path.join(root, 'manifest.json'), JSON.stringify({ manifest_version: 3, background: { service_worker: 'targets/x/missing.js' } }));
  fs.writeFileSync(path.join(root, 'targets/x/manifest.patch.json'), '{}');
  assert.throws(() => build('x', path.join(tmp(), 'out'), root), /not packaged: targets\/x\/missing\.js/); // output stays outside the sources
});

test('the output directory can only replace an earlier build: it never deletes anything else', () => {
  const work = tmp();
  fs.writeFileSync(path.join(work, 'precious.txt'), 'do not delete');
  const stray = path.join(work, 'notes');
  fs.mkdirSync(stray);
  fs.writeFileSync(path.join(stray, 'todo.txt'), 'x');
  const insideSources = path.join(ROOT, 'src');

  for (const bad of [path.parse(work).root, os.homedir(), process.cwd(), ROOT, path.dirname(ROOT), insideSources, path.join(ROOT, 'newdir'), stray]) {
    assert.throws(() => build('chrome', bad), /refusing/, `must refuse ${bad}`);
  }
  assert.ok(fs.existsSync(path.join(work, 'precious.txt')) && fs.existsSync(path.join(stray, 'todo.txt')), 'nothing was deleted');
  assert.ok(fs.existsSync(path.join(ROOT, 'src', 'platform.js')), 'the sources are intact');
});

test('a symlink cannot smuggle a protected directory past the check', () => {
  const link = path.join(tmp(), 'looks-harmless');
  fs.symlinkSync(os.homedir(), link);
  assert.throws(() => assertSafeOutput(link), /refusing/);
});

test('a fresh, an empty and a previously built directory are all fine, and rebuilding replaces the old build', () => {
  const base = tmp();
  const fresh = path.join(base, 'fresh');
  build('chrome', fresh);
  fs.writeFileSync(path.join(fresh, 'src', 'stale.js'), 'from an older build');
  build('chrome', fresh);
  assert.ok(!fs.existsSync(path.join(fresh, 'src', 'stale.js')));
  const empty = path.join(base, 'empty');
  fs.mkdirSync(empty);
  build('firefox', empty);
  assert.ok(fs.existsSync(path.join(empty, 'manifest.json')));
});

test('Firefox: the data declaration says the extension handles mail, and never claims to collect nothing', () => {
  // Plume passes recipients and message text to a local program that sends them on, which Mozilla counts
  // as transmission. "none" would be a false statement.
  const { required } = buildManifest('firefox').browser_specific_settings.gecko.data_collection_permissions;
  assert.ok(required.includes('personalCommunications'));
  assert.ok(!required.includes('none'));
});

test('a directory whose manifest belongs to another extension is never deleted', () => {
  const dir = tmp();
  fs.writeFileSync(path.join(dir, 'manifest.json'), JSON.stringify({ name: 'Someone Elses Extension' }));
  fs.writeFileSync(path.join(dir, 'work.js'), 'precious');
  assert.throws(() => build('chrome', dir), /refusing to replace/);
  assert.ok(fs.existsSync(path.join(dir, 'work.js')), 'nothing was deleted');
  const broken = tmp();
  fs.writeFileSync(path.join(broken, 'manifest.json'), 'not json at all');
  assert.throws(() => build('chrome', broken), /refusing to replace/);
});
