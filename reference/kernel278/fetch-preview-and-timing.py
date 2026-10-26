"""Read private selected-focus JPEG and AF timings; keep all scene pixels outside sources."""
from pathlib import Path
import hashlib,json,shlex
import host
R=Path(__file__).resolve().parent;P=host.PRIVATE
proof=json.loads((R/'af-selected-preview-validation.json').read_text());assert proof['error'] is None
code=r'''
from pathlib import Path
import json
fixed=json.loads(Path('/var/lib/samurai/k278-native-af-r1/summary-private.json').read_text());ae=json.loads(Path('/var/lib/samurai/k278-ae-af-r1/capture-private.json').read_text())
rows=[]
for summary,data in zip(fixed['public'],fixed['runs']):
 frames=data['frames'];focused=[f for f in frames if f['af_state']==2]
 if focused:
  start=next(f for f in frames if f['af_state']==1)
  rows.append(dict(scenario=summary['scenario'],first_scanning_index=start['queued_index'],first_focused_index=focused[0]['queued_index'],capture_timestamp_seconds_to_focus=(focused[0]['timestamp_ns']-start['timestamp_ns'])/1e9))
frames=ae['frames'];start=next(f for f in frames if f['af_state']==1);end=next(f for f in frames if f['af_state']==2)
rows.append(dict(scenario='automatic-exposure',first_scanning_index=start['queued_index'],first_focused_index=end['queued_index'],capture_timestamp_seconds_to_focus=(end['timestamp_ns']-start['timestamp_ns'])/1e9))
image=json.loads(Path('/var/lib/samurai/k278-af-selected-preview/summary-private.json').read_text())['phase']['jpeg']
print(json.dumps(dict(rows=rows,image=image)))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=20);private=json.loads(q.stdout);(P/'af-timing-and-photo-private.json').write_bytes(q.stdout)
photo=private['image'];assert photo['sha256']==proof['jpeg']['sha256'];target=P/'af-selected-preview-private.jpg';assert not target.exists()
fetch="from pathlib import Path;import sys,hashlib;b=Path(%r).read_bytes();assert hashlib.sha256(b).hexdigest()==%r;sys.stdout.buffer.write(b)"%(photo['path'],photo['sha256'])
q=host.ssh('python3 -c '+shlex.quote(fetch),timeout=30);assert len(q.stdout)==photo['bytes'] and hashlib.sha256(q.stdout).hexdigest()==photo['sha256'];target.write_bytes(q.stdout)
report=dict(stage=278,rows=private['rows'],instrumented_paired_capture_not_uninstrumented_preview=True,scene_pixels_private=True,jpeg_sha256=photo['sha256'])
(R/'af-timing-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
