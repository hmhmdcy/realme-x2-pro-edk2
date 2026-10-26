"""Only11 missing exact filenames in official v3.24 pool; never substitute version or digest."""
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
APK=Path('/home/cy122/pmos-samurai-rootfs01/work/apk.static')
KEYS=Path('/home/cy122/pmos-samurai-rootfs01/work/config_apk_keys')
sha=lambda b:hashlib.sha256(b).hexdigest()
os.umask(0o077)
partial=json.loads((HERE/'partial304-result.json').read_bytes())
closure={p['name']:p for p in json.loads((BASE/'closure-private.json').read_bytes())}
targets=[closure[e['name']] for e in partial['remaining_missing']]
out=BASE/'official-v324-exact-pool';out.mkdir(mode=0o700)

def one(p):
    url=p['official_url'].replace('/alpine/edge/','/alpine/v3.24/')
    row={'name':p['name'],'version':p['version'],'url':url,'expected_index_C':p['index_fields']['C']}
    try:
        with urllib.request.urlopen(url,timeout=35) as response:
            assert response.url==url
            raw=response.read(int(p['index_fields']['S'])+1)
        path=out/p['filename'];path.write_bytes(raw)
        row.update(path=str(path),sha256=sha(raw),bytes=len(raw))
        verify=subprocess.run([str(APK),'--keys-dir',str(KEYS),'verify',str(path)],capture_output=True,timeout=30)
        (out/(p['name']+'-verify.log')).write_bytes(verify.stdout+verify.stderr)
        assert verify.returncode==0,('signature',verify.returncode)
        index=out/(p['name']+'-index.tar.gz')
        indexed=subprocess.run([str(APK),'--keys-dir',str(KEYS),'index','--rewrite-arch','aarch64','--output',str(index),str(path)],capture_output=True,timeout=30)
        (out/(p['name']+'-index.log')).write_bytes(indexed.stdout+indexed.stderr)
        assert indexed.returncode==0,('index',indexed.returncode)
        with tarfile.open(index,mode='r:gz') as t:
            text=t.extractfile('APKINDEX').read().decode()
        fields=dict(l.split(':',1) for l in text.splitlines() if ':' in l)
        row['actual_index_C']=fields.get('C')
        for key in ['P','V','A','C','c','S']:
            assert fields.get(key)==p['index_fields'].get(key),(key,fields.get(key),p['index_fields'].get(key))
        for key in ['D','p']:
            assert set(fields.get(key,'').split())==set((p['index_fields'].get(key) or '').split()),key
        row.update(accepted=True,signature_verified=True,exact_frozen_index_digest_and_metadata=True)
    except Exception as e:
        row.update(accepted=False,error=repr(e))
    return row
results=[]
with ThreadPoolExecutor(max_workers=4) as pool:
    for f in as_completed([pool.submit(one,p) for p in targets]):results.append(f.result())
result={'scope':'11 missing exact versions, one official stable pool; no new version/recipe/dependency solve',
        'attempted':11,'accepted':[p for p in results if p['accepted']],
        'rejected':[p for p in results if not p['accepted']],
        'private_install_or_build':False,'source_sha256':sha(Path(__file__).read_bytes())}
(HERE/'same-version-pool-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
