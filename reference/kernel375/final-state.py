from pathlib import Path
import json,shlex
import host
HERE=Path(__file__).resolve().parent
assert json.loads((HERE/'camera-runtime-validation.json').read_text())['passed']
assert json.loads((HERE/'boot-runtime-validation.json').read_text())['passed']
exec(compile((HERE/'current-health.py').read_text(),str(HERE/'current-health.py'),'exec'))
health=json.loads((HERE/'current-health-validation.json').read_text());assert health['healthy']
code=r'''
from pathlib import Path
import json
workers=[]
for p in Path('/proc').glob('[0-9]*'):
 try:
  if (p/'stat').read_text().rsplit(')',1)[1].split()[0]=='Z':continue
  args=(p/'cmdline').read_bytes().split(b'\0')
  if any(a.startswith((b'/var/lib/samurai/k374-',b'/var/lib/samurai/k375-')) and a.endswith((b'/worker.py',b'/snapshot-collector.py')) for a in args):workers.append(int(p.name))
 except OSError:pass
clocks={}
for line in Path('/sys/kernel/debug/clk/clk_summary').read_text().splitlines():
 fields=line.split()
 if fields and any(fields[0].startswith('cam_cc_'+n+'_') for n in ['icp','bps','ipe_0','ipe_1']):clocks[fields[0]]=int(fields[1])
dt=Path('/sys/firmware/devicetree/base');nodes=[str(p) for p in [dt/'soc@0/samurai-icp356-boot@ac10000',*[dt/'reserved-memory'/('samurai-icp356-'+n+'-iova') for n in ['fw','shared','heap','trace']]] if p.exists()]
rails={(p/'name').read_text().strip():dict(state=(p/'state').read_text().strip(),users=int((p/'num_users').read_text())) for p in Path('/sys/class/regulator').glob('regulator.*') if (p/'name').read_text().startswith(('cam-main-','cam-front-','cam-rear-','cam-tele-'))}
print(json.dumps(dict(boot_guard374_matches=Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k374-recovered/boot-id-private.txt').read_bytes(),
 workers=workers,icp_modules=[p.name for p in Path('/sys/module').glob('*icp*')],clocks=clocks,temporary_dt_nodes=nodes,rails=rails,
 temporary_firmware_absent=not Path('/lib/firmware/qcom/sm8150/samurai-icp356.elf').exists(),
 static_icp_status=(dt/'soc@0/icp@ac10000/status').read_bytes().rstrip(b'\0').decode())))
'''
d=json.loads(host.ssh('python3 -c '+shlex.quote(code),timeout=25).stdout)
d.update(stage=375,current_boot_guard_stage=374,current_health=health,normal_camera_capture_passed=True,full_hfi_lifecycle_passed=True,icp_image_sessions_tested=False,candidate_permanently_installed=False)
d['passed']=bool(d['boot_guard374_matches'] and not d['workers'] and not d['icp_modules'] and not d['temporary_dt_nodes'] and d['temporary_firmware_absent'] and d['static_icp_status']=='disabled' and len(d['clocks'])==17 and not any(d['clocks'].values()) and len(d['rails'])==9 and all(v==dict(state='disabled',users=0) for v in d['rails'].values()) and all(v=='suspended' for v in health['camera_pm'].values()))
(HERE/'final-state-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2));assert d['passed']
