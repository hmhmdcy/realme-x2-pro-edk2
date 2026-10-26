"""Fresh actual-k293 identity, partitions and idle camera resources before transition."""
from pathlib import Path
import json
import host
ROOT=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import hashlib,json,os,subprocess
r=Path('/var/lib/samurai')
assert os.uname().version.startswith('#293 ') and os.uname().release=='7.3.0-rc6-rmx1931-samurai-k293+'
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k293-work/boot-id-private.txt').read_bytes()
sha=lambda p:hashlib.file_digest(Path(p).open('rb'),'sha256').hexdigest()
assert sha('/dev/disk/by-partlabel/boot')=='0d6bbc0255fc7a44340b2c2c6a20f2bfa807f683f69dd20a3fb130d961dc4c64'
assert sha('/dev/disk/by-partlabel/logdump')=='be6e413e27cd8914d64ff111e6e7b99941f7dac471c9e2c477e8ee6a2112cf74'
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
for name in ['ac4a000.cci','ac4b000.cci','acb3000.camss']:
 assert Path('/sys/bus/platform/devices',name,'power/runtime_status').read_text().strip()=='suspended'
for p in Path('/sys/class/regulator').glob('regulator.*'):
 if (p/'name').read_text().strip().startswith(('cam-front-','cam-rear-','cam-main-','cam-tele-')):
  assert (p/'state').read_text().strip()=='disabled' and (p/'num_users').read_text().strip()=='0'
assert not (r/'k294-tools').exists();(r/'k294-tools').mkdir(mode=0o700)
print(json.dumps(dict(stage=294,current_kernel_build=293,boot_and_logdump_verified=True,camera_resources_idle=True,new_tools_directory_prepared=True,no_services_stopped=True)))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=25)
report=json.loads(q.stdout);(ROOT/'pre-transition-health-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(q.stdout.decode())
