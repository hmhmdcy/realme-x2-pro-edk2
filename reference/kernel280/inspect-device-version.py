"""Read existing version logs and dynamic-debug sites, without powering devices."""
from pathlib import Path
import json
import host

ROOT = Path(__file__).resolve().parent
code = r'''
from pathlib import Path
import json,os,re,subprocess
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k276-work/boot-id-private.txt').read_bytes()
kernel=subprocess.check_output(['dmesg'],text=True)
rows=[line for line in kernel.splitlines() if re.search(r'(?:VFE|CSID).*HW Version',line)]
debug=Path('/sys/kernel/debug/dynamic_debug/control')
sites=[]
if debug.exists():
 for line in debug.read_text().splitlines():
  if '/camss/' in line and ('HW Version' in line or 'hw_version' in line):sites.append(line)
print(json.dumps(dict(release=os.uname().release,version_logs=rows,dynamic_debug_sites=sites)))
'''
run = host.ssh('python3 -', input=code.encode(), timeout=25)
(host.PRIVATE / 'device-version-inspection-private.json').write_bytes(run.stdout)
data = json.loads(run.stdout)
(ROOT / 'device-version-existing-logs.json').write_text(json.dumps(dict(stage=280, **data,
    no_camera_operations=True), indent=2) + '\n')
print(json.dumps(data, indent=2))
