"""Fetch and verify only the fourteen solver-selected application additions."""
from pathlib import Path
import json
import re
import sys
import host

R=Path(__file__).resolve().parent
audit=json.loads((R/'libcamera-gui-audit-validation.json').read_text())
assert audit['snapshot_simulation_exit']==0 and audit['no_package_transaction']
packages=[]
for line in audit['package_actions']:
 match=re.fullmatch(r'\(\s*\d+/14\) Installing (\S+) \(([^)]+)\)',line)
 if match:packages.append(dict(name=match[1],version=match[2]))
assert len(packages)==14 and not any('Upgrading ' in line or 'Purging ' in line for line in audit['package_actions'])
code=r'''
from pathlib import Path
import hashlib,json,os,subprocess,sys,tarfile,time
os.umask(0o077);r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
assert json.loads((r/'k240-megapixels-startup/state-private.json').read_text())['state']=='terminal'
out=r/'k240-snapshot-packages';assert not out.exists();out.mkdir(mode=0o700)
state=dict(state='running',phase='fetch',pid=os.getpid(),start_ticks=Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]);(out/'state-private.json').write_text(json.dumps(state,indent=2)+'\n')
packages=json.loads(sys.argv[1]);requests=[p['name']+'='+p['version'] for p in packages]
assert len(packages)==14 and len(set(p['name'] for p in packages))==14
before=Path('/lib/apk/db/installed').read_bytes();world=Path('/etc/apk/world').read_bytes()
assert sum(l.startswith(b'P:') for l in before.splitlines())==944
(out/'installed-before-private.txt').write_bytes(before);(out/'world-before-private.txt').write_bytes(world)
repos={str(p):p.read_bytes().hex() for p in [Path('/etc/apk/repositories'),*Path('/etc/apk/repositories.d').glob('*')] if p.is_file()}
(out/'repositories-before-private.json').write_text(json.dumps(repos,indent=2)+'\n')
target=out/'apks';target.mkdir(mode=0o700)
with (out/'fetch-private.log').open('xb') as log:
 result=subprocess.run(['apk','fetch','--output',str(target),*requests],stdout=log,stderr=subprocess.STDOUT,timeout=150)
assert result.returncode==0
manifest=[]
for p in packages:
 path=target/(p['name']+'-'+p['version']+'.apk');assert path.is_file()
 result=subprocess.run(['apk','verify',str(path)],capture_output=True,timeout=15)
 (out/(p['name']+'-verify-private.log')).write_bytes(result.stdout+result.stderr);assert result.returncode==0
 with tarfile.open(path,'r:gz') as archive:
  member=archive.getmember('.PKGINFO');assert member.isfile() and member.size<65536
  values={k:v for line in archive.extractfile(member).read().decode().splitlines() if ' = ' in line for k,v in [line.split(' = ',1)]}
  assert values['pkgname']==p['name'] and values['pkgver']==p['version'] and values['arch']=='aarch64'
 manifest.append(dict(**p,file=path.name,bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
assert before==Path('/lib/apk/db/installed').read_bytes() and world==Path('/etc/apk/world').read_bytes()
(out/'manifest.json').write_text(json.dumps(dict(stage=240,packages=manifest),indent=2)+'\n')
state.update(state='terminal',phase='verified',exit_code=0);(out/'state-private.json').write_text(json.dumps(state,indent=2)+'\n')
report=dict(stage=240,signed_distribution_packages_fetched_and_verified=14,exact_names_versions_arch_verified=True,
 existing944_package_database_and_world_unchanged=True,packages=manifest,download_bytes=sum(p['bytes'] for p in manifest),
 no_package_transaction=True,no_camera_capture=True)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
mode=sys.argv[1:];assert mode in [[],['--apk3-name-selectors']]
context='k240-snapshot-packages'
if mode:
 failure=json.loads((host.PRIVATE/'snapshot-fetch-first-failure-inspection-private.json').read_text())
 assert not failure['worker_alive'] and failure['packages_present']==0
 code=code.replace("out=r/'k240-snapshot-packages'", "out=r/'k240-snapshot-packages-r2'")
 code=code.replace("requests=[p['name']+'='+p['version'] for p in packages]", "requests=[p['name'] for p in packages]")
 context='k240-snapshot-packages-r2'
 (R/'snapshot-fetch-first-failure-validation.json').write_text(json.dumps(dict(stage=240,
   native_apk3_fetch_uses_query_name_selectors_by_default=True,
   constraint_expressions_rejected_before_any_download=True,first_worker_confirmed_dead_and_marked_terminal=True,
   r2_uses_names_then_verifies_every_exact_version=True,no_package_transaction=True),indent=2)+'\n')
p=host.PRIVATE/'current-work-private.json';state=json.loads(p.read_text())
state.update(state='Fetching signed Snapshot application candidate; no installation yet',active_native_context='/var/lib/samurai/'+context,next='Wait for this exact host fetch handle, inspect its actual terminal state; preserve all camera/source candidates')
p.write_text(json.dumps(state,indent=2)+'\n')
# Package expressions contain only names/versions already parsed from native APK.
payload=json.dumps(packages,separators=(',',':'))
assert re.fullmatch(r'[A-Za-z0-9_.,:{}"\[\]-]+',payload)
result=host.ssh("python3 - '"+payload+"'",input=code.encode(),timeout=190)
(host.PRIVATE/'snapshot-fetch-host-private.log').write_bytes(result.stdout+result.stderr)
report=json.loads(result.stdout);(R/'snapshot-fetch-validation.json').write_text(json.dumps(report,indent=2)+'\n')
state=json.loads(p.read_text());state.update(state='Signed Snapshot14 application candidate verified; no installation yet',active_native_context=None,next='Inspect signed packages and native exact-only-additions simulation; install application without upgrading existing r15/desktop stack')
p.write_text(json.dumps(state,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='packages'}))
