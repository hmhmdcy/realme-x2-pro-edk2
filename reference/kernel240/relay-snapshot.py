"""Relay exact distro APKs through the host, retain native signature verification."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import re
import shlex
import tarfile
import urllib.parse
import urllib.request
import host

R=Path(__file__).resolve().parent;P=host.PRIVATE
query=json.loads((P/'snapshot-url-query-network-enabled-private.json').read_text());assert query['exit_code']==0
urls=query['stdout'].splitlines();assert len(urls)==14
actions=json.loads((R/'libcamera-gui-audit-validation.json').read_text())['package_actions']
expected={}
for line in actions:
 m=re.fullmatch(r'\(\s*\d+/14\) Installing (\S+) \(([^)]+)\)',line)
 if m:expected[m[1]+'-'+m[2]+'.apk']=dict(name=m[1],version=m[2])
assert len(expected)==14
target=P/'snapshot-distro-apks';target.mkdir(mode=0o700,exist_ok=True)
def fetch(url):
 parsed=urllib.parse.urlsplit(url);name=Path(parsed.path).name
 assert parsed.scheme=='https' and parsed.hostname=='dl-cdn.alpinelinux.org' and not parsed.username
 assert parsed.path.startswith('/alpine/edge/') and name in expected
 path=target/name
 if not path.exists():
  req=urllib.request.Request(url,headers={'User-Agent':'samurai-linux-camera-integration'})
  with urllib.request.urlopen(req,timeout=30) as response:
   assert urllib.parse.urlsplit(response.url).scheme=='https'
   data=response.read(32*1024**2);assert not response.read(1)
  path.write_bytes(data)
 with tarfile.open(path,'r:gz') as archive:
  member=archive.getmember('.PKGINFO');assert member.isfile() and member.size<65536
  fields={k:v for line in archive.extractfile(member).read().decode().splitlines() if ' = ' in line for k,v in [line.split(' = ',1)]}
  assert fields['pkgname']==expected[name]['name'] and fields['pkgver']==expected[name]['version'] and fields['arch']=='aarch64'
 return dict(**expected[name],file=name,url=url,bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
with ThreadPoolExecutor(max_workers=4) as pool:records=list(pool.map(fetch,urls))
assert len({p['file'] for p in records})==14
(P/'snapshot-distro-manifest-private.json').write_text(json.dumps(dict(stage=240,packages=records),indent=2)+'\n')
print(json.dumps(dict(stage=240,host_https_packages_downloaded=14,bytes=sum(p['bytes'] for p in records))),flush=True)
setup=r'''
from pathlib import Path
import json,os,sys
os.umask(0o077);r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
old=r/'k240-snapshot-packages-r2';assert json.loads((old/'state-private.json').read_text())['state']=='terminal'
assert Path('/lib/apk/db/installed').read_bytes()==(old/'installed-before-private.txt').read_bytes()
out=r/'k240-snapshot-host-packages';assert not out.exists();out.mkdir(mode=0o700);(out/'apks').mkdir(mode=0o700)
for name in ['installed-before-private.txt','world-before-private.txt','repositories-before-private.json']:(out/name).write_bytes((old/name).read_bytes())
(out/'manifest.json').write_bytes(sys.stdin.buffer.read());print('host package relay stage created; original944 unchanged')
'''
host.ssh('python3 -c '+shlex.quote(setup),input=json.dumps(dict(stage=240,packages=records)).encode(),timeout=15)
state_path=P/'current-work-private.json';state=json.loads(state_path.read_text())
state.update(state='Host Snapshot14 packages downloaded; bounded USB relay and native signature verification in progress',
 active_native_context='/var/lib/samurai/k240-snapshot-host-packages',next='Wait for this exact relay handle; no installation before all hashes and native APK signatures verify')
state_path.write_text(json.dumps(state,indent=2)+'\n')
for item in records:
 data=(target/item['file']).read_bytes()
 for offset in range(0,len(data),48*1024):
  block=data[offset:offset+48*1024]
  remote='/var/lib/samurai/k240-snapshot-host-packages/apks/'+item['file']
  code="from pathlib import Path;import os,sys;p=Path("+repr(remote)+");assert (p.stat().st_size if p.exists() else 0)=="+str(offset)+";b=sys.stdin.buffer.read();assert len(b)=="+str(len(block))+";f=p.open('ab');assert f.write(b)==len(b);f.close()"
  host.ssh('python3 -c '+shlex.quote(code),input=block,timeout=25)
 print(json.dumps(dict(relayed=item['name'],bytes=item['bytes'])),flush=True)
verify=r'''
from pathlib import Path
import hashlib,json,subprocess
r=Path('/var/lib/samurai');out=r/'k240-snapshot-host-packages'
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
manifest=json.loads((out/'manifest.json').read_text());assert len(manifest['packages'])==14
for item in manifest['packages']:
 p=out/'apks'/item['file'];assert p.stat().st_size==item['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256']
 result=subprocess.run(['apk','verify',str(p)],capture_output=True,timeout=15)
 (out/(item['name']+'-verify-private.log')).write_bytes(result.stdout+result.stderr);assert result.returncode==0
assert Path('/lib/apk/db/installed').read_bytes()==(out/'installed-before-private.txt').read_bytes()
assert Path('/etc/apk/world').read_bytes()==(out/'world-before-private.txt').read_bytes()
report=dict(stage=240,host_https_exact_distribution_apks=14,native_phone_original_trusted_keys_verified=True,
 all_file_sizes_hashes_and_versions_verified=True,bounded_usb_chunk_bytes=48*1024,
 original944_package_records_world_unchanged=True,no_package_transaction=True)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
result=host.ssh('python3 -',input=verify.encode(),timeout=60)
(P/'snapshot-relay-verify-host-private.log').write_bytes(result.stdout+result.stderr)
report=json.loads(result.stdout);(R/'snapshot-relay-validation.json').write_text(json.dumps(report,indent=2)+'\n')
state=json.loads(state_path.read_text());state.update(state='Snapshot14 exact signed packages staged and native-verified; no installation yet',active_native_context=None,active_fetch_session=None,next='Native offline exact14 add-only simulation, install Snapshot, inspect desktop/PipeWire preview path')
state_path.write_text(json.dumps(state,indent=2)+'\n')
print(json.dumps(report))
