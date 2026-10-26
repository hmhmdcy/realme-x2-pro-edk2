"""Revalidate USB enumeration separately from original-key handset identity."""
from pathlib import Path
import json,subprocess
import host
HERE=Path(__file__).resolve().parent
base=host.previous.previous.base
code="from pathlib import Path;import json,os;print(json.dumps(dict(same_298_guard=Path('/var/lib/samurai/k298-work/boot-id-private.txt').read_bytes()==Path('/proc/sys/kernel/random/boot_id').read_bytes(),expected_model=Path('/sys/firmware/devicetree/base/model').read_bytes()==b'Realme X2 Pro (RMX1931CN)\\0',release=os.uname().release,build=os.uname().version,taint=int(Path('/proc/sys/kernel/tainted').read_text()))))"
records=[]
for kind,address in [('usb','169.254.42.1'),('wifi',json.loads((host.PRIVATE.parent/'kernel303/fresh-working-endpoint-private.json').read_text())['IPAddress'])]:
 try:
  q=subprocess.run([base.SSH,'-T',*base.OPTIONS,'-4','-o','HostKeyAlias=169.254.42.1','root@'+address,'python3 -'],
      input=code.encode(),capture_output=True,timeout=15)
  (host.PRIVATE/(kind+'-transport-recheck-private.log')).write_bytes(q.stdout+q.stderr)
  record=dict(kind=kind,exit=q.returncode,responsive=q.returncode==0)
  if q.returncode==0:
   proof=json.loads(q.stdout);record.update(proof);assert proof['expected_model']
 except subprocess.TimeoutExpired as e:
  (host.PRIVATE/(kind+'-transport-recheck-private.log')).write_bytes((e.stdout or b'')+(e.stderr or b''))
  record=dict(kind=kind,responsive=False,timed_out=True)
 records.append(record)
report=dict(stage=305,strict_original_host_key=True,no_device_mutation=True,probes=records)
(HERE/'transport-recheck-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
