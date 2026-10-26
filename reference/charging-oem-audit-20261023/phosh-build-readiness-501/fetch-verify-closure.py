"""Fetch exact frozen closure from official URLs; verify with real host apk and frozen index identity."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import hashlib
import io
import json
import os
import shutil
import subprocess
import tarfile
import time
import urllib.parse
import urllib.request

HERE=Path(__file__).resolve().parent
BASE=Path('/home/cy122/charging-management-20261023/phosh-external-power-build-501-r1')
ROOT=BASE/'root'
SEED=Path('/home/cy122/x2pro-linux/libcamera214-root')
APK=Path('/home/cy122/pmos-samurai-rootfs01/work/apk.static')
KEYS=Path('/home/cy122/pmos-samurai-rootfs01/work/config_apk_keys')
sha=lambda b:hashlib.sha256(b).hexdigest()
os.umask(0o077)
closure=json.loads((BASE/'closure-private.json').read_bytes())
assert len(closure)==315
copy=json.loads((HERE/'private-copy-and-solver-result.json').read_bytes())
abi=json.loads((HERE/'closure-abi-result.json').read_bytes())
assert abi['differing_runtime_providers']==[]
assert sha(APK.read_bytes())==copy['apk_static_sha256']
db=(ROOT/'lib/apk/db/installed').read_bytes();world=(ROOT/'etc/apk/world').read_bytes()
out=BASE/'downloads';out.mkdir(mode=0o700)
inventory=json.loads((HERE/'inventory-result.json').read_bytes())
cached=[Path(p['path']) for c in inventory['apk_caches'] for p in c['files'] if p['path'].endswith('.apk')]

def pkginfo(raw):
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz',ignore_zeros=True) as tar:
        member=tar.getmember('.PKGINFO');assert member.size<2*1024*1024
        text=tar.extractfile(member).read().decode()
    fields={}
    for line in text.splitlines():
        if ' = ' in line:
            k,v=line.split(' = ',1);fields.setdefault(k,[]).append(v)
    return fields

def check(raw,p):
    assert len(raw)==int(p['index_fields']['S']),(p['name'],'size')
    f=pkginfo(raw)
    for key,wanted in [('pkgname',p['name']),('pkgver',p['version']),('arch',p['arch']),('commit',p['index_fields']['c'])]:
        assert f.get(key)==[wanted],(p['name'],key,f.get(key),wanted)
    for key,field in [('depend','D'),('provides','p')]:
        assert set(f.get(key,[]))==set((p['index_fields'][field] or '').split()),(p['name'],key)
    return f

def one(p):
    raw=None;source=None
    prefix=p['name']+'-'+p['version']
    for path in cached:
        if path.name.startswith(prefix+'.') and path.stat().st_size==int(p['index_fields']['S']):
            candidate=path.read_bytes()
            try:check(candidate,p)
            except (AssertionError,tarfile.TarError,UnicodeError):continue
            raw=candidate;source={'cache':str(path)};break
    if raw is None:
        with urllib.request.urlopen(p['official_url'],timeout=45) as response:
            final=response.url;url=urllib.parse.urlsplit(final)
            assert url.scheme=='https' and url.hostname=='dl-cdn.alpinelinux.org',final
            raw=response.read(int(p['index_fields']['S'])+1)
        source={'official_url':p['official_url'],'final_url':final}
    check(raw,p)
    path=out/p['filename']
    with path.open('xb') as f:f.write(raw)
    return {'name':p['name'],'version':p['version'],'arch':p['arch'],'path':str(path),
             'sha256':sha(raw),'bytes':len(raw),'index_checksum':p['index_fields']['C'],**source}

start=time.monotonic();records=[];errors=[]
state={'phase':'fetching-exact-closure','terminal':False,'requested':315,'completed':0,'errors':[],
       'downloads_directory':str(out),'source_sha256':sha(Path(__file__).read_bytes())}
def save():
    (BASE/'download-state-private.json').write_text(json.dumps(state,indent=2)+'\n')
save()
with ThreadPoolExecutor(max_workers=4) as pool:
    pending={pool.submit(one,p):p for p in closure}
    for future in as_completed(pending):
        p=pending[future]
        try:records.append(future.result())
        except Exception as e:errors.append({'name':p['name'],'version':p['version'],'error':repr(e)})
        state.update(completed=len(records),errors=errors)
        save()
(BASE/'download-records-private.json').write_text(json.dumps(sorted(records,key=lambda p:p['name']),indent=2)+'\n')
if errors:
    state.update(phase='exact-download-failed-no-substitution',terminal=True,seconds=round(time.monotonic()-start,3))
    save();(HERE/'download-result.json').write_text(json.dumps(state,indent=2)+'\n')
    print(json.dumps(state,indent=2));raise SystemExit(1)
paths=[str(out/p['filename']) for p in closure]
verify=subprocess.run([str(APK),'--keys-dir',str(KEYS),'verify',*paths],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180)
(BASE/'verify-signatures-private.log').write_bytes(verify.stdout)
state.update(signature_returncode=verify.returncode,signature_log_sha256=sha(verify.stdout))
assert verify.returncode==0,verify.stdout.decode(errors='replace')[-5000:]
index=BASE/'downloaded-identity-index.tar.gz'
indexed=subprocess.run([str(APK),'index','--output',str(index),*paths],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180)
(BASE/'index-downloaded-private.log').write_bytes(indexed.stdout)
state.update(identity_index_returncode=indexed.returncode)
assert indexed.returncode==0,indexed.stdout.decode(errors='replace')[-5000:]
with tarfile.open(index,mode='r:gz') as tar:
    text=tar.extractfile('APKINDEX').read().decode()
actual={}
for block in text.split('\n\n'):
    f=dict(l.split(':',1) for l in block.splitlines() if ':' in l)
    if 'P' in f:actual[f['P']]=f
assert len(actual)==315
for p in closure:
    f=actual[p['name']]
    for key in ['P','V','A','C','c']:
        assert f.get(key)==p['index_fields'].get(key),(p['name'],key)
    for key in ['D','p']:
        assert set(f.get(key,'').split())==set((p['index_fields'].get(key) or '').split()),(p['name'],key)
assert db==(ROOT/'lib/apk/db/installed').read_bytes() and world==(ROOT/'etc/apk/world').read_bytes()
assert sha((SEED/'lib/apk/db/installed').read_bytes())==copy['original_db_sha256']
assert sha((SEED/'etc/apk/world').read_bytes())==copy['original_world_sha256']
state.update(phase='verified-exact-closure-ready-for-private-install',terminal=True,passed=True,
             actual_package_count=315,all_upstream_signatures_verified=True,
             real_apk_computed_index_C_and_metadata_match_frozen_indexes=True,
             cached=sum('cache' in p for p in records),downloaded=sum('official_url' in p for p in records),
             bytes=sum(p['bytes'] for p in records),seconds=round(time.monotonic()-start,3),
             record_sha256=sha((BASE/'download-records-private.json').read_bytes()),
             identity_index_sha256=sha(index.read_bytes()),original_and_private_db_world_unchanged=True,
             private_install_performed=False)
save();(HERE/'download-result.json').write_text(json.dumps(state,indent=2)+'\n')
print(json.dumps(state,indent=2))
