"""Install the seven verified packages while camera/desktop services are stopped."""
from pathlib import Path
import json
import host
R=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import hashlib,json,os,stat,subprocess,traceback
r=Path('/var/lib/samurai');out=r/'k273-main-transaction';stage=r/'k273-main-candidates'
state=dict(stage=273,state='package-preflight',terminal=False,pid=os.getpid());marker=out/'packages-state-private.json';assert not marker.exists()
def save():marker.write_text(json.dumps(state,indent=2)+'\n')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def records(path):
 result={}
 for block in Path(path).read_bytes().split(b'\n\n'):
  if not block.strip():continue
  name=next(l[2:].decode() for l in block.splitlines() if l.startswith(b'P:'));result[name]=block
 return result
save()
try:
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k270-work/boot-id-private.txt').read_bytes()
 assert json.loads((r/'k273-quiesce/state-private.json').read_text())['exit_code']==0
 assert subprocess.run(['pgrep','-u','10000'],capture_output=True).returncode==1
 assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
 tree=Path('/usr/lib/modules')/os.uname().release;oldmods=json.loads((out/'module-inventory-before-private.json').read_text())
 now={str(p.relative_to(tree)):sha(p) for p in tree.rglob('*.ko')}
 assert len(now)==775 and all(now[n]==v for n,v in oldmods.items()) and not Path('/sys/module/s5kgw1').exists()
 old=json.loads((out/'old-manifest-private.json').read_text());new=json.loads((out/'new-manifest-private.json').read_text())
 selected={x['name'] for x in new['packages']};assert len(selected)==7
 backup=out/'backup/lib/apk/db/installed';assert sha('/lib/apk/db/installed')==sha(backup)
 before=records(backup);assert len(before)==961
 state['state']='native-seven-package-upgrade';save()
 q=subprocess.run(['apk','--no-network','--repositories-file',str(out/'candidate-repositories.list'),'add','samurai-camera-stack=0.1.0-r16'],capture_output=True,text=True,timeout=60)
 (out/'native-install-private.log').write_text(q.stdout+q.stderr);assert q.returncode==0
 for pkg in new['packages']:
  for name,item in pkg['files'].items():
   p=Path('/')/name
   if item['kind']=='symlink':assert p.is_symlink() and os.readlink(p)==item['target']
   else:assert not p.is_symlink() and sha(p)==item['sha256'] and stat.S_IMODE(p.stat().st_mode)==item['mode']
 after=records('/lib/apk/db/installed');assert set(before)==set(after) and all(before[n]==after[n] for n in set(before)-selected)
 Path('/etc/apk/repositories.d/60-samurai-camera.list').write_text('ndx file://'+str(stage/'forward/packages.adb')+'\n')
 requests=[p['name']+'='+p['version'] for p in old['packages']]
 q=subprocess.run(['apk','--no-network','--repositories-file',str(out/'rollback-repositories.list'),'add','--simulate',*requests],capture_output=True,text=True,timeout=30)
 (out/'native-rollback-simulate-private.log').write_text(q.stdout+q.stderr);assert q.returncode==0
 actions=[x for x in q.stdout.splitlines() if x.startswith('(')];assert len(actions)==7 and all('Downgrading ' in x for x in actions)
 assert {str(p.relative_to(tree)):sha(p) for p in tree.rglob('*.ko')}==now
 report=dict(stage=273,seven_packages_upgraded=True,framework_version='99990.7.2-r21',config_version='0.1.0-r16',
  package_count=961,other954_package_records_unchanged=True,all_new_payloads_verified=True,
  modules_unchanged_during_package_update=True,native_seven_downgrades_simulated=True,
  desktop_and_camera_services_quiesced=True,new_sensor_not_loaded=True,ready_for_controlled_reboot=True)
 (out/'packages-summary.json').write_text(json.dumps(report,indent=2)+'\n');os.sync();state.update(state='terminal',terminal=True,exit_code=0);save();print(json.dumps(report))
except BaseException:
 (out/'packages-failure-private.txt').write_text(traceback.format_exc());state.update(state='failed',terminal=True,exit_code=1);save();raise
'''
q=host.ssh('python3 -',input=code.encode(),timeout=110,check=False)
(host.PRIVATE/'packages-install-response-private.log').write_bytes(q.stdout+q.stderr)
assert q.returncode==0 and q.stdout,'Inspect the package transaction and live phone before any recovery'
d=json.loads(q.stdout);(R/'packages-install-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
