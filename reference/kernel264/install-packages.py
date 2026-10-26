"""Install only the paired, tested native packages; retain exact rollback state."""
from pathlib import Path
import json,shlex
import host
R=Path(__file__).parent;proof=json.loads((R/'package-build-validation.json').read_text())
for mode in [6000057,6000058,6000059,6000060,6000061,6000062,6000063]:
 d=json.loads((R/('run-'+str(mode)+'-validation.json')).read_text());assert d['diagnostic_completed'];assert d['probe_result']['core_candidate_sha256']==proof[0]['payload_sha256'] and d['probe_result']['spa_candidate_sha256']==proof[1]['payload_sha256']
sim=json.loads((R/'package-simulation-validation.json').read_text());assert sim['all_four_apk_signatures_trusted'] and sim['database_and_world_unchanged']
code=r'''
from pathlib import Path
import hashlib,json,os,re,subprocess,sys
os.umask(0o077);root=Path('/var/lib/samurai');proof=json.loads(sys.argv[1]);out=root/'k264-package-transaction';assert not out.exists();out.mkdir()
state=dict(stage=264,phase='preflight',terminal=False)
def save(phase):state['phase']=phase;(out/'state-private.json').write_text(json.dumps(state,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(args,label):
 p=subprocess.run(args,capture_output=True,timeout=40);(out/(label+'-private.log')).write_bytes(p.stdout+p.stderr);assert p.returncode==0,label;return p
def records(raw):
 return {re.search(r'^P:(.+)$',block,re.M)[1]:block for block in raw.decode().split('\n\n') if re.search(r'^P:(.+)$',block,re.M)}
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k260-work/boot-id-private.txt').read_bytes()
devices=['/sys/bus/i2c/devices/7-0010','/sys/bus/i2c/devices/9-0010','/sys/bus/platform/devices/ac4a000.cci','/sys/bus/platform/devices/ac4b000.cci','/sys/bus/platform/devices/acb3000.camss']
assert all(Path(p,'power/runtime_status').read_text().strip()=='suspended' for p in devices)
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
for item in proof:assert sha(Path('/')/item['changed_payload'])==item['original_payload_sha256']
for name in ['installed','scripts.tar','triggers']:
 p=Path('/lib/apk/db')/name
 if p.exists():(out/(name+'-before-private')).write_bytes(p.read_bytes())
db=Path('/lib/apk/db/installed').read_bytes();world=Path('/etc/apk/world').read_bytes();(out/'world-before-private').write_bytes(world)
names=[i['package'] for i in proof];inputs=root/'k264-package-inputs';new=[str(inputs/(name+'-1.6.9-r2.apk')) for name in names];old=[str(inputs/(name+'-1.6.9-r0.apk')) for name in names]
for item,path in zip(proof,new):assert sha(Path(path))==item['apk_sha256']
run(['apk','verify',*old,*new],'trusted-signatures')
simulation=run(['apk','add','--simulate','--no-network',*new],'install-simulation')
actions=[l for l in (simulation.stdout+simulation.stderr).decode().splitlines() if re.match(r'^\(\s*\d+/',l) and 'Downloading ' not in l]
assert len(actions)==2 and all('Upgrading '+name+' ' in '\n'.join(actions) for name in names)
assert Path('/lib/apk/db/installed').read_bytes()==db and Path('/etc/apk/world').read_bytes()==world
save('install-starting');run(['apk','add','--no-network',*new],'install');save('installed-awaiting-verification')
for item in proof:assert sha(Path('/')/item['changed_payload'])==item['payload_sha256']
before=records(db);after=records(Path('/lib/apk/db/installed').read_bytes());assert set(before)==set(after) and len(after)==961
changed=sorted(n for n in before if before[n]!=after[n]);assert changed==sorted(names),changed
rollback=run(['apk','add','--simulate','--no-network',*old],'rollback-simulation')
lines=[l for l in (rollback.stdout+rollback.stderr).decode().splitlines() if re.match(r'^\(\s*\d+/',l) and 'Downloading ' not in l]
assert len(lines)==2 and all('Downgrading '+name+' ' in '\n'.join(lines) for name in names),lines
world_after=Path('/etc/apk/world').read_bytes();(out/'world-after-private').write_bytes(world_after)
report=dict(stage=264,installed=True,versions={name:'1.6.9-r2' for name in names},payload_sha256={item['changed_payload']:sha(Path('/')/item['changed_payload']) for item in proof},only_package_records_changed=changed,package_count=len(after),rollback_apks_preserved_and_trusted=True,rollback_simulation_actions=lines,world_entries_added=sorted(set(world_after.decode().splitlines())-set(world.decode().splitlines())),service_restart_performed=False,reboot_performed=False,taint=int(Path('/proc/sys/kernel/tainted').read_text()))
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');state['terminal']=True;save('verified');print(json.dumps(report))
'''
r=host.ssh('python3 - '+shlex.quote(json.dumps(proof)),input=code.encode(),timeout=115,check=False);(host.PRIVATE/'package-install-private.log').write_bytes(r.stdout+r.stderr)
assert r.returncode==0,'Inspect the saved transaction state before doing anything else'
d=json.loads(r.stdout);(R/'package-install-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
