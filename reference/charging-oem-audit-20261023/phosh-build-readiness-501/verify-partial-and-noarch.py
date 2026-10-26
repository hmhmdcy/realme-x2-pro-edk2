"""Narrow follow-up: keep failed315 attempt; fetch only its25 noarch rejects, validate304 actual payloads."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import hashlib
import io
import json
import os
import subprocess
import tarfile
import urllib.request

HERE=Path(__file__).resolve().parent
BASE=Path('/home/cy122/charging-management-20261023/phosh-external-power-build-501-r1')
ROOT=BASE/'root'
SEED=Path('/home/cy122/x2pro-linux/libcamera214-root')
APK=Path('/home/cy122/pmos-samurai-rootfs01/work/apk.static')
KEYS=Path('/home/cy122/pmos-samurai-rootfs01/work/config_apk_keys')
sha=lambda b:hashlib.sha256(b).hexdigest()
os.umask(0o077)
attempt=json.loads((HERE/'download-result.json').read_bytes())
assert attempt['terminal'] and attempt['phase']=='exact-download-failed-no-substitution' and attempt['completed']==279
history=HERE/'history-download01';history.mkdir(mode=0o700)
for name in ['fetch-verify-closure.py','download-result.json']:
    (history/name).write_bytes((HERE/name).read_bytes())
closure=json.loads((BASE/'closure-private.json').read_bytes());wanted={p['name']:p for p in closure}
rejected=[wanted[e['name']] for e in attempt['errors'] if "'arch'" in e['error']]
assert len(rejected)==25
out=BASE/'noarch-identity-boundary';out.mkdir(mode=0o700)
records=json.loads((BASE/'download-records-private.json').read_bytes())
errors=[]
def one(p):
    with urllib.request.urlopen(p['official_url'],timeout=45) as response:
        assert response.url==p['official_url']
        raw=response.read(int(p['index_fields']['S'])+1)
    assert len(raw)==int(p['index_fields']['S'])
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz',ignore_zeros=True) as t:
        text=t.extractfile('.PKGINFO').read().decode()
    f={}
    for l in text.splitlines():
        if ' = ' in l:
            k,v=l.split(' = ',1);f.setdefault(k,[]).append(v)
    assert f['arch']==['noarch'] and p['arch']=='aarch64'
    for k,v in [('pkgname',p['name']),('pkgver',p['version']),('commit',p['index_fields']['c'])]:assert f[k]==[v]
    for k,v in [('depend','D'),('provides','p')]:assert set(f.get(k,[]))==set((p['index_fields'][v] or '').split())
    path=out/p['filename'];path.write_bytes(raw)
    return {'name':p['name'],'version':p['version'],'arch':'noarch','index_arch':'aarch64','path':str(path),
             'bytes':len(raw),'sha256':sha(raw),'official_url':p['official_url'],'index_checksum':p['index_fields']['C']}
with ThreadPoolExecutor(max_workers=4) as pool:
    futures={pool.submit(one,p):p for p in rejected}
    for f in as_completed(futures):
        try:records.append(f.result())
        except Exception as e:errors.append({'name':futures[f]['name'],'error':repr(e)})
assert not errors,errors
assert len(records)==304
paths=[p['path'] for p in records]
v=subprocess.run([str(APK),'--keys-dir',str(KEYS),'verify',*paths],capture_output=True,timeout=180)
(BASE/'verify-partial304-private.log').write_bytes(v.stdout+v.stderr)
assert v.returncode==0
index=BASE/'partial304-rewrite-arch-index.tar.gz'
i=subprocess.run([str(APK),'--keys-dir',str(KEYS),'index','--rewrite-arch','aarch64','--output',str(index),*paths],capture_output=True,timeout=180)
(BASE/'index-partial304-rewrite-arch-private.log').write_bytes(i.stdout+i.stderr)
assert i.returncode==0,(i.stdout+i.stderr).decode(errors='replace')[-1500:]
with tarfile.open(index,mode='r:gz') as t:text=t.extractfile('APKINDEX').read().decode()
indexed={}
for b in text.split('\n\n'):
    f=dict(l.split(':',1) for l in b.splitlines() if ':' in l)
    if 'P' in f:indexed[f['P']]=f
assert len(indexed)==304
for p in records:
    f=indexed[p['name']];expected=wanted[p['name']]['index_fields']
    for k in ['P','V','A','C','c']:assert f.get(k)==expected.get(k),(p['name'],k,f.get(k),expected.get(k))
    for k in ['D','p']:assert set(f.get(k,'').split())==set((expected.get(k) or '').split()),(p['name'],k)
copy=json.loads((HERE/'private-copy-and-solver-result.json').read_bytes())
for seed in [SEED,ROOT]:
    assert sha((seed/'lib/apk/db/installed').read_bytes())==copy['original_db_sha256']
    assert sha((seed/'etc/apk/world').read_bytes())==copy['original_world_sha256']
(BASE/'verified304-records-private.json').write_text(json.dumps(sorted(records,key=lambda p:p['name']),indent=2)+'\n')
result={
    'passed_partial_identity_verification':True,'complete_closure':False,'verified_payload_count':304,
    'initial_attempt_receipt_sha256':sha((history/'download-result.json').read_bytes()),
    'noarch_rejections_proven_compatible_projection':25,
    'actual_apk_verify_signature_returncode':v.returncode,'actual_apk_index_rewrite_arch_returncode':i.returncode,
    'all_actual_index_C_and_P_V_A_c_D_p_match_frozen_indexes_after_documented_arch_projection':True,
    'source_semantics':'apk-tools v3.0.8 doc/apk-index.8.scd45-46 and src/app_index.c142-144 explicitly rewrite only pkg->arch in generated index; no payload change',
    'remaining_missing':[e for e in attempt['errors'] if '404' in e['error']],
    'no_retry_of_missing11_or_original279':True,
    'original_and_private_db_world_unchanged':True,'installed_or_built':False,
    'actual_native_apk_sha256':sha(APK.read_bytes()),
    'records_sha256':sha((BASE/'verified304-records-private.json').read_bytes()),
    'index_sha256':sha(index.read_bytes()),
    'verify_log_sha256':sha((BASE/'verify-partial304-private.log').read_bytes()),
    'index_log_sha256':sha((BASE/'index-partial304-rewrite-arch-private.log').read_bytes()),
    'source_sha256':sha(Path(__file__).read_bytes()),
}
(HERE/'partial304-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'verified':304,'noarch_proven':25,'missing':len(result['remaining_missing']),
                  'result_sha256':sha((HERE/'partial304-result.json').read_bytes())},indent=2))
