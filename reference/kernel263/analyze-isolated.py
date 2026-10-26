from pathlib import Path
import json,sys
import host
mode=int(sys.argv[1]);assert mode in [6000002,6000003,6000004,6000005,6000006,6000008]
code=r'''
from pathlib import Path
import collections,hashlib,json,re,sys
mode=sys.argv[1];root=Path('/var/lib/samurai/k263-user')/('isolated-'+mode)
s=(root/'probe-stderr-private.txt').read_text(errors='replace');wp=(root/'wireplumber-private.log').read_text(errors='replace')
samples=[tuple(map(int,m)) for m in re.findall(r'ownership-trace busy=(-?\d+) refs=(\d+) metas=(\d+) fd=(-?\d+)',s)]
stats=[tuple(map(int,m)) for m in re.findall(r'busy-ownership deferrals:(\d+) requeues:(\d+)',wp)]
print(json.dumps(dict(stage=263,mode=int(mode),not_recycled_errors=s.count('was not recycled'),ownership_samples=len(samples),busy_values=dict(collections.Counter(x[0] for x in samples)),ownership_meta_counts=dict(collections.Counter(x[2] for x in samples)),backend_busy_stats=stats,candidate_sha256=hashlib.sha256(Path('/var/lib/samurai/k263-spa/libcamera/libspa-libcamera.so').read_bytes()).hexdigest() if mode in ['6000005','6000006','6000008'] else None,result=json.loads((root/'summary.json').read_text()))))
'''
r=host.ssh('python3 - '+str(mode),input=code.encode())
(host.PRIVATE/('isolation-analysis-'+str(mode)+'-private.json')).write_bytes(r.stdout)
d=json.loads(r.stdout)
(Path(__file__).parent/('isolation-flow-'+str(mode)+'-validation.json')).write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps(d,indent=2))
