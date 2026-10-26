from pathlib import Path
import json
import host
code=r'''
from pathlib import Path
import json,re
p=Path('/var/lib/samurai/k264-snapshot-gui');assert json.loads((p/'state-private.json').read_text())['state']=='terminal'
s=(p/'stderr-private.txt').read_text(errors='replace');pts=[int(x) for x in re.findall(r'pipewiresrc[^\n]* pts (\d+), dts_offset',s)]
report=dict(stage=264,application='snapshot',new_buffers=s.count('got new buffer'),recycle_errors=s.count('was not recycled'),paintable_bus_errors=sum('paintable' in l and 'Bus Error' in l for l in s.splitlines()),sink_render_calls=sum('gtk4paintablesink' in l and 'rendering object' in l for l in s.splitlines()),source_pts_count=len(pts),source_pts_increasing=len(pts)>1 and all(b>a for a,b in zip(pts,pts[1:])),source_pts_span_seconds=(pts[-1]-pts[0])/1e9 if len(pts)>1 else 0,gui_shutter_exercised=True,application_copy_flag_removed=True)
assert report['recycle_errors']==0 and report['paintable_bus_errors']==0 and report['source_pts_increasing'] and report['sink_render_calls']>100
print(json.dumps(report))
'''
r=host.ssh('python3 -',input=code.encode());(host.PRIVATE/'snapshot-flow-private.json').write_bytes(r.stdout)
d=json.loads(r.stdout);(Path(__file__).parent/'snapshot-flow-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
