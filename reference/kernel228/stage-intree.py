"""Stage the genuine in-tree build for the next clean boot, retaining live code."""
from pathlib import Path
import hashlib
import json
import struct
import host

ref = Path(__file__).resolve().parent
build = json.loads((ref / 'intree-build-validation.json').read_text())
native = json.loads((ref / 'native-sensors-validation.json').read_text())
assert len(native['five_real_sensor_streams']) == 5 and native['real_module_pin']['after_close'] == 1


def sections(path):
    raw = path.read_bytes()
    off = struct.unpack_from('<Q', raw, 40)[0]
    size, count, idx = struct.unpack_from('<HHH', raw, 58)
    headers = [struct.unpack_from('<IIQQQQIIQQ', raw, off + i * size) for i in range(count)]
    strings = raw[headers[idx][4]:headers[idx][4] + headers[idx][5]]
    return {strings[h[0]:].split(b'\0', 1)[0].decode(): raw[h[4]:h[4] + h[5]] for h in headers}


old = sections(Path('/home/cy122/x2pro-linux/fastrpc227-publication/candidate/fastrpc.o'))
new = sections(Path('/home/cy122/pmos-samurai-kernel136/kernel/drivers/misc/fastrpc.o'))
names = [n for n in old if n.startswith(('.text', '.init.text', '.exit.text'))]
assert names and all(old[n] == new[n] for n in names)
proof = dict(stage=228, actual_text_sections_identical=True,
             sections={n: len(old[n]) for n in names}, source_sha256=build['source_sha256'],
             external_sha256='7ca5d442fb8351f841dcae3d16e4f981d9b08e7326b42c674f7ceaf4f08bdc0a',
             intree_sha256=build['module_sha256'], real_intree_target=True)
(ref / 'intree-code-equivalence-validation.json').write_text(json.dumps(proof, indent=2) + '\n')
host.upload(host.PRIVATE / 'fastrpc228-intree-private.ko', '/var/lib/samurai/k228-tools/fastrpc-intree-private.ko')
host.upload(ref / 'intree-build-validation.json', '/var/lib/samurai/k228-tools/intree-build-validation.json')
code = r'''
from pathlib import Path
import hashlib,json,os,stat,struct,subprocess
root=Path('/var/lib/samurai');out=root/'k228-intree-stage';assert not out.exists()
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes();assert boot==(root/'k228-runtime/boot-id-private.txt').read_bytes()
assert int(Path('/proc/sys/kernel/tainted').read_text())==4096
assert {p.parent.name:p.read_text().strip() for p in Path('/sys/module').glob('*/taint') if p.read_text().strip()}=={'fastrpc':'O'}
sha=lambda b:hashlib.sha256(b).hexdigest()
tree=Path('/usr/lib/modules')/os.uname().release;relative='kernel/drivers/misc/fastrpc.ko';module=tree/relative
old=module.read_bytes();assert sha(old)=='7ca5d442fb8351f841dcae3d16e4f981d9b08e7326b42c674f7ceaf4f08bdc0a'
new=(root/'k228-tools/fastrpc-intree-private.ko').read_bytes();build=json.loads((root/'k228-tools/intree-build-validation.json').read_text())
assert sha(new)==build['module_sha256']=='2abde0ead81c2feb78f639da2ab29d7c3e29654a9d013a098418b232a5cfd794'
assert subprocess.check_output(['modinfo','-F','intree',str(root/'k228-tools/fastrpc-intree-private.ko')],text=True).strip()=='Y'
loaded=Path('/sys/module/fastrpc/notes/.note.gnu.build-id').read_bytes()
out.mkdir(mode=0o700);(out/'boot-id-private.txt').write_bytes(boot);(out/'external-module-before-private.ko').write_bytes(old);(out/'loaded-note-before-private.bin').write_bytes(loaded)
state=out/'transaction-state-private.json';state.write_text(json.dumps(dict(state='prepared',reloaded=False))+'\n')
temp=module.with_name('.fastrpc.ko.k228-intree-new');meta=module.stat();fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,stat.S_IMODE(meta.st_mode))
try:
 with os.fdopen(fd,'wb',closefd=False) as output:output.write(new);output.flush()
 os.fchown(fd,meta.st_uid,meta.st_gid);os.fchmod(fd,stat.S_IMODE(meta.st_mode));os.fsync(fd)
finally:os.close(fd)
assert temp.read_bytes()==new;os.replace(temp,module);d=os.open(module.parent,os.O_RDONLY|os.O_DIRECTORY)
try:os.fsync(d)
finally:os.close(d)
expected=json.loads((root/'k228-module-install/module-inventory-after-private.json').read_text());expected[relative]=sha(new)
actual={str(p.relative_to(tree)):sha(p.read_bytes()) for p in tree.rglob('*') if p.is_file()};assert actual==expected
(out/'module-inventory-after-private.json').write_text(json.dumps(actual,indent=2)+'\n');(out/'module-tree-after.sha256').write_text(''.join(v+'  '+n+'\n' for n,v in sorted(actual.items())))
assert Path('/sys/module/fastrpc/notes/.note.gnu.build-id').read_bytes()==loaded
assert Path('/lib/apk/db/installed').read_bytes()==(root/'k228-baseline/installed-before-private.txt').read_bytes()
state.write_text(json.dumps(dict(state='verified',reloaded=False,next_clean_boot_required=True))+'\n')
report=dict(stage=228,intree_default_staged=True,intree_module_sha256=sha(new),intree_module_bytes=len(new),unrelated785_module_files_unchanged=True,
 running_external_candidate_kept=True,current_taint=4096,current_module_refcount=int(Path('/sys/module/fastrpc/refcnt').read_text()),
 no_unload_or_reload=True,no_reboot_sent=True,package_database_unchanged=True,next_clean_boot_required=True)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
result = host.ssh('python3 -', input=code.encode(), timeout=45)
(host.PRIVATE / 'intree-stage-host-private.log').write_bytes(result.stdout + result.stderr)
report = json.loads(result.stdout)
(ref / 'intree-stage-validation.json').write_text(json.dumps(report, indent=2) + '\n')
state = json.loads((host.PRIVATE / 'current-work-private.json').read_text())
state.update(state='native functional fix verified; canonical in-tree source/build accepted and2abde default staged; running7ca external OOT only; next clean boot',
             active_native_session=None,active_native_context=None,transition_pending=False,
             guard='/var/lib/samurai/k228-runtime/boot-id-private.txt',
             next='Fresh current-boot baseline with known OOT4096 only, controlled quiesce/reboot without flash, then require intree loaded-note and taint0 and sensor/pin tests')
(host.PRIVATE / 'current-work-private.json').write_text(json.dumps(state, indent=2) + '\n')
print(json.dumps(report))
print(json.dumps(proof))
