from pathlib import Path
import difflib, hashlib, json, shutil
here = Path(__file__).resolve().parent
repo = here.parents[1]
out = Path('/mnt/e/edk2-samurai-out/kernel206')
vendor = out.parent / 'kernel88'
radio = repo / 'linux-port/radio'
base = (vendor / 'tqftpserv/tqftpserv.c.before').read_bytes()
final = (out / 'tftp-build-r5/tqftpserv.c').read_bytes()
assert hashlib.sha256(base).hexdigest() == 'bb15a562d036fc49055145a248a9a126d305ed0bbbbf79768d47ea957d92982d'
assert hashlib.sha256(final).hexdigest() == '20b9d630ffdf89d7fae4c19ce25710c87fd36dde3ac850eb9bc1eed6f45c04eb'
(radio / 'tqftpserv-work-files.patch').write_text(''.join(difflib.unified_diff(base.decode().splitlines(True), final.decode().splitlines(True), fromfile='a/tqftpserv.c', tofile='b/tqftpserv.c')))
shutil.copyfile(repo / 'reference/kernel88/ro-firmware.c', radio / 'ro-firmware.c')
manifest = json.loads((repo / 'reference/kernel88/qrtr-tools-source-manifest.json').read_text())
needed = {'linux-msm/tqftpserv': {'tqftpserv.c', 'translate.h', 'list.h', 'LICENSE'}, 'linux-msm/qrtr': {'include/libqrtr.h', 'include/logging.h', 'include/ns.h', 'lib/qrtr.c', 'lib/logging.c', 'LICENSE'}}
selected = [record for record in manifest if record['path'] in needed.get(record['repo'], set())]
for record in selected:
    needed[record['repo']].remove(record['path'])
# This snapshot uses the logging header at qrtr/lib/logging.h on some revisions.
unmatched = {key: sorted(value) for key, value in needed.items() if value}
result = dict(source_records=selected, unresolved_optional_source_paths=unmatched, patched_server_source_sha256=hashlib.sha256(final).hexdigest(), own_sources={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [radio / 'samurai-tftp-ram.c', radio / 'ro-firmware.c', radio / 'samurai-wifi.sh', radio / 'tqftpserv-work-files.patch']})
(radio / 'source-lock.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(dict(pinned_files=len(selected), unresolved_optional_source_paths=unmatched, full_patch_from_pinned_upstream_recorded=True)))
