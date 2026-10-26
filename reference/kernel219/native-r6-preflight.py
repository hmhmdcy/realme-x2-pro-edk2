"""Record current installation and simulate exactly seven coherent upgrades."""
from pathlib import Path
import host,json
here=Path(__file__).resolve().parent
for kind,pattern,w,h in [('raw',0,2304,1728),('raw',2,2304,1728),('rgb',2,2296,1728),('rgb',0,2296,1728)]:
 r=json.loads((here/f'isolated-r6-{w}x{h}-{kind}-pattern{pattern}-default-validation.json').read_text())
 assert r['program_exit']==0 and len(r['frames'])==6 and r['all_formats_restored'] and r['media_graph_restored'] and r['sensor_controls_restored']
 assert r['taint']==0 and not any(r['fault_delta'].values())
code=r'''
from pathlib import Path
import hashlib,json,os,stat,subprocess
os.umask(0o077);root=Path('/var/lib/samurai');stage=root/'k219-r6-package-candidates';out=root/'k219-r6-package-transaction'
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k219-runtime/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert Path('/lib/apk/db/installed').read_bytes()==(root/'k219-baseline/installed-before-private.txt').read_bytes()
assert not out.exists();out.mkdir(mode=0o700)
old=json.loads((root/'k214-package-candidates/forward-manifest.json').read_text())
new=json.loads((stage/'forward-manifest.json').read_text());assert {p['name'] for p in old['packages']}=={p['name'] for p in new['packages']}
for package in old['packages']:
 for relative,item in package['files'].items():
  p=Path('/')/relative
  if item['kind']=='symlink':assert p.is_symlink() and os.readlink(p)==item['target']
  else:assert hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256'] and stat.S_IMODE(p.stat().st_mode)==item['mode']
repositories={}
for p in [Path('/etc/apk/repositories'),*sorted(Path('/etc/apk/repositories.d').glob('*'))]:
 if p.is_file():repositories[str(p)]=dict(bytes=p.read_bytes().hex(),mode=stat.S_IMODE(p.stat().st_mode))
(out/'repositories-before-private.json').write_text(json.dumps(repositories,indent=2)+'\n')
(out/'world-before-private.txt').write_bytes(Path('/etc/apk/world').read_bytes())
(out/'installed-before-private.txt').write_bytes(Path('/lib/apk/db/installed').read_bytes())
(out/'config-before-private.yaml').write_bytes(Path('/etc/libcamera/configuration.yaml').read_bytes())
assert sum(l.startswith('P:') for l in Path('/lib/apk/db/installed').read_text().splitlines())==944
repo=Path('/etc/apk/repositories.d/60-samurai-camera.list');assert repo.exists() and 'k214-package-candidates/forward/packages.adb' in repo.read_text()
repos=out/'candidate-repositories.list';repos.write_text('ndx file://'+str(stage/'forward/packages.adb')+'\n')
p=subprocess.run(['apk','--no-network','--repositories-file',str(repos),'add','--simulate','samurai-camera-stack=0.1.0-r1'],capture_output=True,text=True,timeout=30)
(out/'native-forward-dry-private.log').write_text(p.stdout+p.stderr);assert p.returncode==0
actions=[line for line in p.stdout.splitlines() if line.startswith('(')];assert len(actions)==7
for package in new['packages']:
 previous='0.1.0-r0' if package['name'].startswith('samurai-camera-') else '99990.7.2-r5'
 assert any(('Upgrading '+package['name']+' ('+previous+' -> '+package['version']+')') in line for line in actions)
assert not any('Installing ' in l or 'Purging ' in l or 'Removing ' in l for l in actions)
assert Path('/lib/apk/db/installed').read_bytes()==(out/'installed-before-private.txt').read_bytes()
report=dict(stage=219,native_phone_solver_passed=True,exactly_seven_camera_upgrades_no_additions_or_removals=True,
 all_current_camera_payloads_match_r5_rollback=True,current_944_package_database_world_repositories_and_configuration_saved=True,
 signed_repositories_only=True,same_current219_boot=True,package_transaction_not_sent=True)
(out/'preflight-summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=70);(host.PRIVATE/'r6-preflight-host-private.log').write_bytes(p.stdout+p.stderr)
r=json.loads(p.stdout);(here/'r6-native-preflight-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
