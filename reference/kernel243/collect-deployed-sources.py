from pathlib import Path
import hashlib,json
r=Path('/var/lib/samurai');files={};hashes={}
for name in ['k243-diag-python','k243-diag-python-r2','k243-diag-python-r3','k243-diag-python-r4']:
 p=r/name/'diag_transport.py';b=p.read_bytes();files[name]=b.decode();hashes[name]=hashlib.sha256(b).hexdigest()
print(json.dumps({'report':{'stage':243,'deployed_library_sha256':hashes,'read_only':True},'private':files}))
