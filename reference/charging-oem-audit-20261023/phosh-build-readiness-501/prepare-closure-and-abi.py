"""Read frozen solver/index/actual runtime metadata into a pinned closure and ABI comparison."""
from pathlib import Path
import hashlib
import io
import json
import re
import tarfile

HERE = Path(__file__).resolve().parent
BASE = Path('/home/cy122/charging-management-20261023/phosh-external-power-build-501-r1')
ROOT = BASE/'root'
SEED = Path('/home/cy122/x2pro-linux/libcamera214-root')
sha = lambda b:hashlib.sha256(b).hexdigest()
def parse(text):
    out = {}
    for b in text.split('\n\n'):
        f = dict(l.split(':',1) for l in b.splitlines() if ':' in l)
        if 'P' in f:
            out[f['P']] = f
    return out

copy = json.loads((HERE/'private-copy-and-solver-result.json').read_bytes())
assert copy['solver_returncode']==0 and copy['terminal']
log=(BASE/'solver-private.log').read_text()
rows=re.findall(r'^\(\s*(\d+)/(\d+)\) Installing ([^ ]+) \(([^)]+)\)$',log,re.M)
assert len(rows)==315 and [int(r[0]) for r in rows]==list(range(1,316))
assert {int(r[1]) for r in rows}=={315}
assert not re.search(r'Upgrading|Downgrading|Removing|ERROR|WARNING',log)
all_packages = {}
for name,pin in copy['index_pins'].items():
    raw=Path(pin['private']).read_bytes()
    assert sha(raw)==pin['sha256']
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as t:
        packages=parse(t.extractfile('APKINDEX').read().decode())
    for package,fields in packages.items():
        all_packages.setdefault(package,[]).append({'repository':name,'fields':fields,'index_sha256':pin['sha256']})
closure=[]
for _,_,name,version in rows:
    choices=[p for p in all_packages[name] if p['fields']['V']==version and p['fields']['A'] in ['aarch64','noarch']]
    assert choices and all(p['fields']==choices[0]['fields'] for p in choices),name
    p=choices[0]
    f=p['fields'];assert f['V']==version and f['A'] in ['aarch64','noarch']
    closure.append({'name':name,'version':version,'arch':f['A'],'repository':p['repository'],
                    'index_sha256':p['index_sha256'],'index_fields':{k:f.get(k) for k in ['P','V','A','C','c','D','p','S','I']},
                    'filename':name+'-'+version+'.apk',
                    'official_url':'https://dl-cdn.alpinelinux.org/alpine/edge/'+p['repository']+'/aarch64/'+name+'-'+version+'.apk'})
snapshot=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/image501-activation/image501-gauge-live-001/postboot-r1-04-private/stdout-private.json')
actualraw=snapshot.read_bytes()
actual=parse(json.loads(actualraw)['raw']['package_db'])
seed=parse((ROOT/'lib/apk/db/installed').read_text())
expected=dict(seed)
expected.update({p['name']:p['index_fields'] for p in closure})
def provider(packages,requirement):
    key=re.split(r'[<>=~]',requirement,maxsplit=1)[0]
    choices=[(n,p) for n,p in packages.items() if key in [re.split(r'[<>=~]',s,maxsplit=1)[0] for s in (p.get('p') or '').split()]]
    assert len(choices)==1,(requirement,[p[0] for p in choices])
    return choices[0]
abi=[]
for requirement in actual['phosh']['D'].split():
    if not requirement.startswith('so:'):
        continue
    oldname,old=provider(actual,requirement)
    newname,new=provider(expected,requirement)
    keys=['V','A','C','c','D','p']
    differences={k:{'actual':old.get(k),'private_expected':new.get(k)} for k in keys if old.get(k)!=new.get(k)}
    abi.append({'requirement':requirement,'actual_package':oldname,'private_expected_package':newname,
                'actual_version':old['V'],'private_expected_version':new['V'],
                'same_name':oldname==newname,'metadata_differences':differences})
summary={
    'full_runtime_db_cache_sha256':sha(actualraw),'actual_package_count':len(actual),
    'scope':'Only providers of the installed Phosh direct ELF SONAME requirements compared; not a 315-package device matrix',
    'phosh_direct_soname_count':len(abi),'direct_soname_provider_comparison':abi,
    'differing_runtime_providers':[x for x in abi if not x['same_name'] or x['metadata_differences']],
    'libphosh_actual':{k:actual.get('libphosh',{}).get(k) for k in ['P','V','A','C','c','D','p']},
    'new_packages':315,'upgrades_downgrades_or_removals':0,
    'indexed_compressed_bytes':sum(int(p['index_fields']['S']) for p in closure),
    'all_closure_versions_from_two_frozen_verified_by_solver_indexes':True,
    'private_install_or_build_performed':False,
    'original_seed_db_world_unchanged':sha((SEED/'lib/apk/db/installed').read_bytes())==copy['original_db_sha256'] and sha((SEED/'etc/apk/world').read_bytes())==copy['original_world_sha256'],
    'program_sha256':sha(Path(__file__).read_bytes()),
}
(BASE/'closure-private.json').write_text(json.dumps(closure,indent=2)+'\n')
(HERE/'closure-abi-result.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({'new_packages':len(closure),'indexed_download_bytes':summary['indexed_compressed_bytes'],
                  'soname_count':len(abi),'differences':summary['differing_runtime_providers'],
                  'result_sha256':sha((HERE/'closure-abi-result.json').read_bytes())},indent=2))
