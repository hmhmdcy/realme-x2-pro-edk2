"""Preserve current rollback APKs and simulate the exact three-package transaction."""
from pathlib import Path
import hashlib,json,shlex
import host
R=Path(__file__).parent;proof=json.loads((R/'package-build-validation.json').read_text())
for run in [12,13,14]:
 d=json.loads((R/('ownership-'+str(run)+'-validation.json')).read_text());assert d['completed'] and d['held_changes']==0 and d['missing_busy']==0 and d['held_without_extra_loan']==0
for item in proof:
 for version,digest in [(item['original_version'],item['original_apk_sha256']),('1.6.9-r3',item['apk_sha256'])]:
  name=item['package']+'-'+version+'.apk';data=(host.PRIVATE/name).read_bytes();assert hashlib.sha256(data).hexdigest()==digest
  code="from pathlib import Path;import os,sys;os.umask(0o077);p=Path('/var/lib/samurai/k265-package-inputs');p.mkdir(exist_ok=True);f=p/"+repr(name)+";data=sys.stdin.buffer.read();assert not f.exists() or f.read_bytes()==data;f.write_bytes(data)"
  host.ssh('python3 -c '+shlex.quote(code),input=data)
code=r'''
from pathlib import Path
import hashlib,json,os,re,subprocess,sys
os.umask(0o077);root=Path('/var/lib/samurai');proof=json.loads(sys.argv[1]);out=root/'k265-package-simulation';assert not out.exists();out.mkdir()
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k260-work/boot-id-private.txt').read_bytes()
inputs=root/'k265-package-inputs';files=[inputs/(i['package']+'-'+v+'.apk') for i in proof for v in [i['original_version'],'1.6.9-r3']]
q=subprocess.run(['apk','verify',*map(str,files)],capture_output=True,timeout=20);(out/'trusted-signatures-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0
for item in proof:
 assert hashlib.sha256((inputs/(item['package']+'-1.6.9-r3.apk')).read_bytes()).hexdigest()==item['apk_sha256']
 assert hashlib.sha256((Path('/')/item['changed_payload']).read_bytes()).hexdigest()==item['original_payload_sha256']
db=Path('/lib/apk/db/installed').read_bytes();world=Path('/etc/apk/world').read_bytes()
new=[str(inputs/(i['package']+'-1.6.9-r3.apk')) for i in proof]
q=subprocess.run(['apk','add','--simulate','--no-network',*new],capture_output=True,timeout=30);(out/'simulation-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0
actions=[l for l in (q.stdout+q.stderr).decode().splitlines() if re.match(r'^\(\s*\d+/',l) and 'Downloading ' not in l]
assert len(actions)==3 and all('Upgrading '+i['package']+' ' in '\n'.join(actions) for i in proof),actions
assert Path('/lib/apk/db/installed').read_bytes()==db and Path('/etc/apk/world').read_bytes()==world
report=dict(stage=265,installed=False,all_six_apk_signatures_trusted=True,simulation_actions=actions,database_and_world_unchanged=True,apk_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
q=host.ssh('python3 - '+shlex.quote(json.dumps(proof)),input=code.encode(),timeout=65);(host.PRIVATE/'package-simulation-private.json').write_bytes(q.stdout);d=json.loads(q.stdout);(R/'package-simulation-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))

