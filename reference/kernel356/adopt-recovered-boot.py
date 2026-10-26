from pathlib import Path
import json,shlex
import host
P=host.PRIVATE;facts=json.loads((P/'recovered-state-private.json').read_text());expected=facts['/proc/sys/kernel/random/boot_id'];assert facts['camss_build_note_sha256']=='0227d29bb5129e2fc69866529147b21b902d441c855f848fd5eaa3093c590297'
code=r'''
from pathlib import Path
import hashlib,json,os
current=Path('/proc/sys/kernel/random/boot_id').read_text().strip();assert current==EXPECTED
assert Path('/proc/sys/kernel/osrelease').read_text().strip()=='7.3.0-rc6-rmx1931-samurai-k298+'
assert Path('/sys/firmware/devicetree/base/model').read_bytes().rstrip(b'\0')==b'Realme X2 Pro (RMX1931CN)'
assert hashlib.sha256(Path('/sys/module/qcom_camss/notes/.note.gnu.build-id').read_bytes()).hexdigest()=='0227d29bb5129e2fc69866529147b21b902d441c855f848fd5eaa3093c590297'
assert not Path('/sys/module/qcom_camss_icp_a5_core').exists() and not Path('/sys/module/camss_icp_a5_boot_test').exists()
root=Path('/var/lib/samurai/k356-recovered');root.mkdir(mode=0o700,exist_ok=True);guard=root/'boot-id-private.txt';raw=Path('/proc/sys/kernel/random/boot_id').read_bytes()
if guard.exists():assert guard.read_bytes()==raw
else:
 with guard.open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
descriptor=os.open(root,os.O_RDONLY|os.O_DIRECTORY);os.fsync(descriptor);os.close(descriptor)
print(json.dumps(dict(guard_path=str(guard),original_305_guard_preserved=True,identity_and_camss_verified=True)))
'''.replace('EXPECTED',repr(expected))
r=host.raw_ssh('python3 -',input=code.encode(),timeout=25);(P/'recovered-boot-adoption-private.json').write_bytes(r.stdout);print(r.stdout.decode())
