"""Check restoration once after the final bounded experiment."""
from pathlib import Path
import json,shlex
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
code=r'''from pathlib import Path
import hashlib,json,subprocess
d=Path('/sys/bus/platform/devices/ac10000.icp');services={}
for name in ['pipewire','wireplumber']:
 ps=[]
 for p in Path('/proc').glob('[0-9]*'):
  try:
   if (p/'comm').read_text().strip()==name and (p/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z':ps.append(p)
  except OSError:pass
 assert len(ps)==1
 services[name]=dict(count=1,uid=ps[0].stat().st_uid)
modules={}
for n in ['qcom_camss','camss_icp_a5_m2m','qcom_camss_icp_a5_core']:
 p=Path(subprocess.check_output(['modinfo','-n',n],text=True).strip());modules[n]=dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),note=hashlib.sha256(Path('/sys/module',n,'notes/.note.gnu.build-id').read_bytes()).hexdigest())
print(json.dumps(dict(services=services,modules=modules,m2m=json.loads((d/'m2m_status').read_text()),core=json.loads((d/'state').read_text()),pm={n:Path('/sys/bus/platform/devices',n,'power/runtime_status').read_text().strip() for n in ['ac10000.icp','acb3000.camss','ac4a000.cci','ac4b000.cci']},taint=int(Path('/proc/sys/kernel/tainted').read_text()),library_sha256=hashlib.sha256(Path('/usr/lib/libcamera.so.0.7.2').read_bytes()).hexdigest())))
'''
q=host.ssh('python3 -c '+shlex.quote(code),timeout=25);q.check_returncode();data=json.loads(q.stdout);(P/'final-device-private.json').write_bytes(q.stdout)
expected=json.loads((HERE.parent/'kernel440/current-state-validation.json').read_text());baseline=json.loads((P/'preflight-private.json').read_text())
for n,row in data['modules'].items():assert row['sha256']==expected['modules'][n]['sha256'] and row['note']==baseline['notes'][n]
assert data['library_sha256']=='0884c73489815132b5f180c303ab5ed2edc4c52f0f7b191365054aa855849a48'
assert all(v=='suspended' for v in data['pm'].values()) and data['taint']==0
assert all(s['uid']==10000 for s in data['services'].values())
assert not any(data['core'][k] for k in ['backing_owned','cpu_enabled','irq_enabled','power_held','remaining_groups','remaining_domains','mapped_bytes','ipe_dma_pending','request_fw_mapped','imported_buffers','imported_bytes'])
s=data['m2m'];assert s['jobs']==s['completed']==s['direct_completed'] and not any(s[k] for k in ['users','running','fatal','pinned','orphans','failed','cancelled','first_error'])
r=dict(stage=441,formal440_r32_library_and_434_modules_restored=True,loaded_module_notes_match_baseline=True,services=data['services'],pm=data['pm'],m2m_epoch_jobs=s['jobs'],resources_released=True,taint=0,candidate_installed=False,passed=True)
(HERE/'current-state-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
