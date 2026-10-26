from pathlib import Path
import json,re
import host
code=r'''
from pathlib import Path
import json,re
r=Path('/var/lib/samurai/k263-user/isolated-6000034')
pw=(r/'pipewire-private.log').read_text();wp=(r/'wireplumber-private.log').read_text();victim=(r/'crash-client-stderr-private.txt').read_text()
result=dict(camera_pool_rebuild_messages=pw.count('rebuild camera pool after consumer removal')+wp.count('rebuild camera pool after consumer removal'),backend_start_messages=len(re.findall(r'starting camera ',wp)),backend_stop_messages=len(re.findall(r'stopping camera ',wp)),victim_buffers_before_sigkill=victim.count('got new buffer'),victim_recycle_errors=victim.count('was not recycled'),survivor=json.loads((r/'summary.json').read_text())['clients'][0])
assert result['camera_pool_rebuild_messages']>=1 and result['backend_start_messages']>=2 and result['victim_buffers_before_sigkill']>5
print(json.dumps(result))
'''
r=host.ssh('python3 -',input=code.encode());(host.PRIVATE/'crash-recovery-analysis-private.json').write_bytes(r.stdout)
d=json.loads(r.stdout);(Path(__file__).parent/'crash-recovery-flow-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
