"""Copy paired candidates and originals, verify native trust, and simulate only."""
from pathlib import Path
import hashlib,json,shlex
import host
R=Path(__file__).parent
proof=json.loads((R/'package-build-validation.json').read_text())
for mode in [6000057,6000058,6000059,6000060,6000061,6000062,6000063]:
 d=json.loads((R/('run-'+str(mode)+'-validation.json')).read_text());assert d['diagnostic_completed'] and d['probe_result']['core_candidate_sha256']==proof[0]['payload_sha256'] and d['probe_result']['spa_candidate_sha256']==proof[1]['payload_sha256']
for item in proof:
 for version in ['1.6.9-r0','1.6.9-r2']:
  name=item['package']+'-'+version+'.apk';data=(host.PRIVATE/name).read_bytes()
  code="from pathlib import Path;import os,sys;os.umask(0o077);p=Path('/var/lib/samurai/k264-package-inputs');p.mkdir(exist_ok=True);f=p/"+repr(name)+";data=sys.stdin.buffer.read();assert not f.exists() or f.read_bytes()==data;f.write_bytes(data)"
  host.ssh('python3 -c '+shlex.quote(code),input=data)
code=r'''
from pathlib import Path
import hashlib,json,os,re,subprocess
os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k264-package-simulation';assert not out.exists();out.mkdir()
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k260-work/boot-id-private.txt').read_bytes()
inputs=root/'k264-package-inputs';names=['pipewire-libs','pipewire-spa-libcamera']
files=[inputs/(name+'-'+version+'.apk') for name in names for version in ['1.6.9-r0','1.6.9-r2']]
q=subprocess.run(['apk','verify',*map(str,files)],capture_output=True,timeout=20);(out/'trusted-signatures-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0
db=Path('/lib/apk/db/installed').read_bytes();world=Path('/etc/apk/world').read_bytes()
new=[str(inputs/(name+'-1.6.9-r2.apk')) for name in names]
q=subprocess.run(['apk','add','--simulate','--no-network',*new],capture_output=True,timeout=30);(out/'simulation-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0
actions=[l for l in (q.stdout+q.stderr).decode().splitlines() if re.match(r'^\(\s*\d+/',l) and 'Downloading ' not in l]
assert len(actions)==2 and all('Upgrading '+name+' ' in '\n'.join(actions) for name in names),actions
assert Path('/lib/apk/db/installed').read_bytes()==db and Path('/etc/apk/world').read_bytes()==world
report=dict(stage=264,installed=False,all_four_apk_signatures_trusted=True,simulation_actions=actions,database_and_world_unchanged=True,apk_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
r=host.ssh('python3 -',input=code.encode(),timeout=65);(host.PRIVATE/'package-simulation-private.json').write_bytes(r.stdout)
d=json.loads(r.stdout);(R/'package-simulation-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
