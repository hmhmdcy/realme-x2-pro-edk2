"""Run only after the device has really restarted; preserve the original key."""
from pathlib import Path
import json,shlex
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
before=json.loads((P/'pre-reboot-private.json').read_text())
normal=json.loads((P/'runtime-collected-r3/state.json').read_text())['before_notes']
code='''from pathlib import Path
import hashlib,json,os
before=BEFORE;normal=NORMAL;boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert boot!=before['boot'],'Still the faulted boot; do not touch driver locks'
assert b'realme,samurai' in Path('/sys/firmware/devicetree/base/compatible').read_bytes()
assert os.uname().release==before['release'] and Path('/proc/cmdline').read_text()==before['cmdline']
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert all(sha(r['path'])==r['sha256'] for r in before['formal_disk_modules'].values())
assert all(sha('/sys/module/'+n+'/notes/.note.gnu.build-id')==h for n,h in normal.items())
dev=Path('/sys/bus/platform/devices/ac10000.icp');s=json.loads((dev/'m2m_status').read_text());c=json.loads((dev/'state').read_text())
assert not any(s[k] for k in ['users','running','fatal','pinned','orphans','failed','cancelled','first_error'])
assert not any(c[k] for k in ['backing_owned','cpu_enabled','irq_enabled','power_held','mapped_bytes','ipe_dma_pending','request_fw_mapped','imported_buffers'])
taint=int(Path('/proc/sys/kernel/tainted').read_text());assert not taint&128,'New boot has an Oops'
root=Path('/var/lib/samurai/k429-recovered');root.mkdir(mode=0o700,exist_ok=True);guard=root/'boot-id-private.txt'
if guard.exists():assert guard.read_text().strip()==boot
else:
 with guard.open('x') as f:f.write(boot+'\\n');f.flush();os.fsync(f.fileno())
print(json.dumps(dict(stage=429,guard_path=str(guard),new_boot_verified=True,formal_disk_hashes_and_loaded_notes_verified=True,
 original_key_and_known_hosts_reused=True,old_fault_context_cannot_survive_boot_transition=True,taint=taint,m2m=s,core=c,
 camera_function_and_desktop_services_not_yet_revalidated=True,passed=True)))
'''.replace('BEFORE',repr(before)).replace('NORMAL',repr(normal))
q=host.raw_ssh('python3 -c '+shlex.quote(code),timeout=25);q.check_returncode();data=json.loads(q.stdout)
(P/'postboot-adoption-private.json').write_bytes(q.stdout);data.pop('guard_path')
(HERE/'postboot-validation.json').write_text(json.dumps(data,indent=2)+'\n');print(json.dumps(data,indent=2))
