"""Resolve firmware loader search path and hash the modem set; read only."""
from pathlib import Path
import hashlib,json,subprocess
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k236-runtime/boot-id-private.txt').read_bytes()
param=Path('/sys/module/firmware_class/parameters/path').read_text().strip()
name=next(p for p in Path('/sys/class/remoteproc').glob('*') if (p/'name').read_text().strip()=='modem')
firmware=(name/'firmware').read_text().strip()
release=subprocess.check_output(['uname','-r'],text=True).strip()
paths=[Path(param)/firmware] if param else []
paths += [Path(x)/firmware for x in ['/lib/firmware/updates/'+release,'/lib/firmware/updates','/lib/firmware/'+release,'/lib/firmware']]
checks=[]
for p in paths:
 checks.append(dict(path=str(p),present=p.is_file(),zst_present=Path(str(p)+'.zst').is_file(),xz_present=Path(str(p)+'.xz').is_file()))
matches=[Path(x['path']) for x in checks if x['present']]
report=dict(stage=242,firmware_search_paths_checked=True,uncompressed_candidates=len(matches),readonly=True)
private=dict(loader_parameter=param,requested_firmware=firmware,checks=checks)
if matches:
 base=matches[0].parent;manifest={}
 expected={line.split()[1]:line.split()[0] for line in Path('/etc/samurai-wifi/modem-sha256.txt').read_text().splitlines()}
 for n,digest in expected.items():
  p=base/n
  manifest[n]=dict(present=p.is_file())
  if p.is_file():
   raw=p.read_bytes();manifest[n].update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),matches_deployment=hashlib.sha256(raw).hexdigest()==digest)
 private['manifest']=manifest;private['selected_path']=str(matches[0])
 report.update(modem_files=len(expected),all_present=all(x['present'] for x in manifest.values()),all_match_deployment=all(x.get('matches_deployment',False) for x in manifest.values()))
print(json.dumps(dict(report=report,private=private)))
