"""Parse cached tar/APKINDEX data only; no package tool, network or extraction."""
from pathlib import Path
import hashlib
import io
import json
import re
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sha = lambda b: hashlib.sha256(b).hexdigest()
inventory = json.loads((HERE/'inventory-result.json').read_bytes())
deps = list(inventory['seed']['present_makedepends']) + inventory['seed']['missing_makedepends']
wanted = set(deps + ['phosh', 'libphosh', 'upower', 'gtk+3.0', 'glib', 'xvfb-run', 'xmlstarlet', 'gobject-introspection-dev', 'vala'])
indices = []
all_apks = [p for c in inventory['apk_caches'] for p in c['files'] if p['path'].endswith('.apk')]
cached_missing_direct = {p: [r for r in all_apks if re.match(re.escape(p)+r'-\d', Path(r['path']).name)] for p in inventory['seed']['missing_makedepends']}
for cache in inventory['apk_caches']:
    for item in cache['files']:
        path = Path(item['path'])
        if not path.name.startswith('APKINDEX') or not path.name.endswith('.tar.gz'):
            continue
        raw = path.read_bytes()
        with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as tar:
            member = tar.getmember('APKINDEX')
            assert member.size < 64*1024*1024
            text = tar.extractfile(member).read().decode()
            selected = {}
            architectures = set()
            for block in text.split('\n\n'):
                fields = dict(l.split(':', 1) for l in block.splitlines() if ':' in l)
                if fields.get('A'):
                    architectures.add(fields['A'])
                if fields.get('P') in wanted:
                    selected[fields['P']] = {k: fields.get(k) for k in ['V','A','c','D','p','C']}
            indices.append({'path': str(path), 'sha256': sha(raw), 'architectures':sorted(architectures), 'selected':selected})

archive = Path('/mnt/e/edk2-samurai-out/charging-ui-audit-20261023/phosh-connection-source-r8/phosh-0.57.0.tar.xz')
raw = archive.read_bytes()
assert sha(raw) == '30cd0eb182b92846162ab57516170ca09fe8ce08ef95703ee351af7b9c2b9520'
with tarfile.open(fileobj=io.BytesIO(raw), mode='r:xz') as tar:
    names = set(tar.getnames())
    base = 'phosh-0.57.0/'
    options = tar.extractfile(base+'meson_options.txt').read().decode()
    subprojects = {p.split('/')[2] for p in names if p.startswith(base+'subprojects/') and len(p.split('/'))>=4}
    wrapped = [p for p in sorted(names) if p.startswith(base+'subprojects/') and p.endswith('.wrap')]

report = {
    'cached_inventory_sha256':sha((HERE/'inventory-result.json').read_bytes()),
    'cached_apk_count':len(all_apks),
    'cached_missing_direct_makedepends':cached_missing_direct,
    'cached_index_contents_only_not_new_signature_verification':indices,
    'release_archive_sha256':sha(raw),
    'release_has_subprojects':sorted(subprojects),
    'wrap_files':wrapped,
    'meson_options':options,
    'recipe': {'sha256':sha((ROOT/'reference/charging-ui-audit-20261023/phosh-connection-source-r8/phosh-APKBUILD').read_bytes()),
               'required_explicit_options':['b_lto=true','phoc_tests=disabled','man=true','bindings-lib=true'],
               'checkdepends':['xvfb-run','xmlstarlet']},
    'no_network_package_tool_or_build':True,
    'analysis_program_sha256':sha(Path(__file__).read_bytes()),
}
(HERE/'cached-input-analysis.json').write_text(json.dumps(report,indent=2)+'\n')
available = {}
for index in indices:
    if 'aarch64' in index['architectures']:
        for p, fields in index['selected'].items():
            if fields['A'] in ['aarch64','noarch']:
                available.setdefault(p,set()).add(fields['V'])
print(json.dumps({'cached_apk_count':len(all_apks),'missing_direct_devs_with_cached_apk':[p for p,v in cached_missing_direct.items() if v],
                  'aarch64_cached_index_versions':{p:sorted(v) for p,v in available.items()},
                  'release_has_subprojects':sorted(subprojects),'wrap_files':wrapped,
                  'result_sha256':sha((HERE/'cached-input-analysis.json').read_bytes())},indent=2))
