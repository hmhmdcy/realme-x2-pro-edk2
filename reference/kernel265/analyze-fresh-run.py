from pathlib import Path
import json
import host
code=r'''
from pathlib import Path
import json,re
p=Path('/var/lib/samurai/k265-camera-11');t=(p/'wireplumber-trace-private.log').read_text(errors='replace');ls=t.splitlines()
print(json.dumps(dict(fresh_allocation_count=t.count('fresh image allocation after graph buffer retirement'),interesting=[l for l in ls if any(k in l for k in ['fresh image allocation','starting camera','stopping camera','busy-ownership','alloc_buffers','use_buffers','clear_buffers'])][-45:]),indent=2))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=20);(host.PRIVATE/'fresh-run11-analysis-private.json').write_bytes(q.stdout);print(q.stdout.decode())

