from pathlib import Path
import json,shlex
import host
HERE=Path(__file__).resolve().parent
assert json.loads((HERE/'install-r1-validation.json').read_text())['passed']
code=r'''
from pathlib import Path
import hashlib,json,subprocess
services={};workers=[]
for p in Path('/proc').glob('[0-9]*'):
 try:
  if (p/'stat').read_text().rsplit(')',1)[1].split()[0]=='Z':continue
  name=(p/'comm').read_text().strip()
  if name in ['pipewire','wireplumber']:services.setdefault(name,[]).append(dict(pid=int(p.name),uid=p.stat().st_uid))
  args=(p/'cmdline').read_bytes().split(b'\0')
  if any(a.startswith(b'/var/lib/samurai/k362-') and a.endswith(b'/worker.py') for a in args):workers.append(int(p.name))
 except OSError:pass
module=Path(subprocess.check_output(['modinfo','-n','qcom_camss'],text=True).strip())
names=['acb3000.camss','ac4a000.cci','ac4b000.cci']
facts=dict(kernel=subprocess.check_output(['uname','-r'],text=True).strip(),taint=int(Path('/proc/sys/kernel/tainted').read_text()),
 camss_note_sha256=hashlib.sha256(Path('/sys/module/qcom_camss/notes/.note.gnu.build-id').read_bytes()).hexdigest(),
 camss_disk_sha256=hashlib.sha256(module.read_bytes()).hexdigest(),services=services,workers=workers,
 platforms={n:Path('/sys/bus/platform/devices',n,'power/runtime_status').read_text().strip() for n in names},
 rails={(p/'name').read_text().strip():dict(state=(p/'state').read_text().strip(),users=int((p/'num_users').read_text())) for p in Path('/sys/class/regulator').glob('regulator.*') if (p/'name').read_text().startswith(('cam-main-','cam-front-','cam-rear-','cam-tele-'))},
 icp_modules=[p.name for p in Path('/sys/module').glob('*icp*')])
print(json.dumps(facts))
'''
d=json.loads(host.ssh('python3 -c '+shlex.quote(code),timeout=30).stdout)
proof=json.loads((host.PRIVATE/'install-proof.json').read_text())
d.update(stage=362,ssh='strict_original_key_usb',kernel_image_unchanged=True,installed_module_stage=348)
d['passed']=bool(d['taint']==0 and not d['workers'] and not d['icp_modules'] and d['camss_note_sha256']==proof['candidate_note_sha256'] and
    all(v=='suspended' for v in d['platforms'].values()) and all(v==dict(state='disabled',users=0) for v in d['rails'].values()) and
    all(len(d['services'].get(n,[]))==1 and d['services'][n][0]['uid']==10000 for n in ['pipewire','wireplumber']))
(HERE/'final-state-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2));assert d['passed']
