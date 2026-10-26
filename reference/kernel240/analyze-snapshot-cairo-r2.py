"""Count new source buffers and preview sink renders, never camera pixels."""
from pathlib import Path
import json
import host
R=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import json,re
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
p=r/'k240-snapshot-cairo-r2';assert json.loads((p/'state-private.json').read_text())['state']=='terminal'
text=(p/'stderr-private.txt').read_text(errors='replace')+'\n'+(p/'stdout-private.json').read_text(errors='replace');lines=text.splitlines();trace=(p/'video-buffer-trace-private.txt').read_text()
counts={}
for event in ['vb2_v4l2_buf_done','vb2_v4l2_dqbuf']:
 found=[]
 for line in trace.splitlines():
  m=re.search(r': '+event+r': minor=(\d+) .*timestamp = (\d+).*sequence = (\d+)',line)
  if m:found.append((int(m[1]),int(m[2]),int(m[3]),'|ERROR|' in line))
 counts[event]={}
 for minor in sorted({f[0] for f in found}):
  e=[x for x in found if x[0]==minor]
  counts[event][str(minor)]=dict(count=len(e),unique_sequences=len({x[2] for x in e}),first_sequence=e[0][2],last_sequence=e[-1][2],
   timestamps_increase=all(b[1]>a[1] for a,b in zip(e,e[1:])),error_frames=sum(x[3] for x in e))
new=[x for x in lines if 'got new buffer' in x]
keep=[x for x in lines if 'keepalive' in x.lower()]
renderstats=[x for x in lines if 'rendered:' in x and 'gtk4paintablesink' in x]
sinkrenders=[x for x in lines if 'gtk4paintablesink' in x and 'rendering object' in x]
selected=[]
for line in lines:
 if any(s in line for s in ['we got format','Selected camera','last-camera','Current camera','GL support','Cairo','cairo renderer','Camerabin state','Failed','ERROR','WARN','Using camera','aperture::','snapshot::widgets::camera']):selected.append(line[:600])
report=dict(stage=240,kernel_buffer_events=counts,pipewire_new_buffer_count=len(new),pipewire_keepalive_log_count=len(keep),
 gtk4_preview_render_log_count=len(sinkrenders),gtk4_preview_sink_final_stats=renderstats,
 source_new_buffer_first3=new[:3],source_new_buffer_last3=new[-3:],diagnostic_lines=selected[-45:],
 other_session_diagnostics=[x[:500] for x in lines if ('snapshot::' in x or 'portal' in x.lower() or 'permission' in x.lower()) and not any(w in x.lower() for w in ['gallery','thumbnail','picture','uri','location','using caps'])][-35:],
 no_scene_pixels_read_or_saved=True,no_shutter=True,startup=json.loads((p/'summary.json').read_text()))
(p/'frame-flow-analysis.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=15)
(host.PRIVATE/'snapshot-cairo-r2-analysis-host-private.log').write_bytes(q.stdout+q.stderr)
data=json.loads(q.stdout);(R/'snapshot-cairo-r2-frame-flow-validation.json').write_text(json.dumps(data,indent=2)+'\n')
print(json.dumps(data))
