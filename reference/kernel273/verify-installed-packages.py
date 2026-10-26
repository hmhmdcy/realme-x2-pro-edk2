"""Complete post-install verification without replaying the completed APK upgrade."""
from pathlib import Path
import json
import host
R=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import hashlib,json,os,stat,subprocess
r=Path('/var/lib/samurai');out=r/'k273-main-transaction';marker=out/'packages-verified-state-private.json';assert not marker.exists()
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k270-work/boot-id-private.txt').read_bytes()
oldstate=json.loads((out/'packages-state-private.json').read_text());assert oldstate['terminal'] and oldstate['exit_code']==1
assert not Path('/proc',str(oldstate['pid'])).exists()
assert 'unrecognized option' in (out/'native-rollback-simulate-private.log').read_text()
assert subprocess.run(['pgrep','-u','10000'],capture_output=True).returncode==1 and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def records(p):
 result={}
 for b in Path(p).read_bytes().split(b'\n\n'):
  if b.strip():result[next(l[2:].decode() for l in b.splitlines() if l.startswith(b'P:'))]=b
 return result
old=json.loads((out/'old-manifest-private.json').read_text());new=json.loads((out/'new-manifest-private.json').read_text())
selected={p['name'] for p in new['packages']};before=records(out/'backup/lib/apk/db/installed');after=records('/lib/apk/db/installed')
assert set(before)==set(after) and len(after)==961 and all(before[n]==after[n] for n in set(before)-selected)
count=0
for pkg in new['packages']:
 assert 'V:'+pkg['version'] in after[pkg['name']].decode().splitlines()
 for name,item in pkg['files'].items():
  p=Path('/')/name
  if item['kind']=='symlink':assert p.is_symlink() and os.readlink(p)==item['target']
  else:assert not p.is_symlink() and sha(p)==item['sha256'] and stat.S_IMODE(p.stat().st_mode)==item['mode']
  count+=1
tree=Path('/usr/lib/modules')/os.uname().release;oldmods=json.loads((out/'module-inventory-before-private.json').read_text())
now={str(p.relative_to(tree)):sha(p) for p in tree.rglob('*.ko')}
assert len(now)==775 and set(now)-set(oldmods)=={'kernel/drivers/media/i2c/s5kgw1.ko'} and all(now[n]==v for n,v in oldmods.items())
assert now['kernel/drivers/media/i2c/s5kgw1.ko']==json.loads((out/'summary.json').read_text())['new_module_sha256']
requests=[p['name']+'='+p['version'] for p in old['packages']]
q=subprocess.run(['apk','--no-network','--repositories-file',str(out/'rollback-repositories.list'),'add','--simulate',*requests],capture_output=True,text=True,timeout=30)
(out/'native-rollback-simulate-corrected-private.log').write_text(q.stdout+q.stderr);assert q.returncode==0
actions=[x for x in q.stdout.splitlines() if x.startswith('(')];assert len(actions)==7 and all('Downgrading ' in x for x in actions)
assert all(any('Downgrading '+p['name']+' (' in x for x in actions) for p in old['packages'])
assert not Path('/sys/module/s5kgw1').exists()
report=dict(stage=273,seven_packages_upgraded=True,framework_version='99990.7.2-r21',config_version='0.1.0-r16',
 package_count=961,other954_package_records_unchanged=True,verified_payload_records=count,all_new_payloads_verified=True,
 existing774_modules_preserved=True,native_seven_downgrades_simulated=True,
 desktop_and_camera_services_quiesced=True,new_sensor_not_loaded=True,ready_for_controlled_reboot=True,
 original_postinstall_argument_failure_retained=True,apk_install_not_repeated=True)
(out/'packages-verified-summary.json').write_text(json.dumps(report,indent=2)+'\n')
marker.write_text(json.dumps(dict(state='verified',terminal=True,exit_code=0,pid=os.getpid()),indent=2)+'\n');os.sync();print(json.dumps(report))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=45,check=False)
(host.PRIVATE/'packages-verify-corrected-response-private.log').write_bytes(q.stdout+q.stderr)
assert q.returncode==0 and q.stdout,'Inspect corrected verification before retrying'
d=json.loads(q.stdout);(R/'packages-install-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
