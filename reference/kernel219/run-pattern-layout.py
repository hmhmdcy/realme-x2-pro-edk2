"""Measure only the sensor-generated test pattern, not room colours or images."""
from pathlib import Path
import gzip,hashlib,host,json,shlex,sys
here=Path(__file__).resolve().parent
assert sys.argv[1:] in [['2304','1728'],['4608','3456']];w,h=map(int,sys.argv[1:]);cell=2 if w==4608 else 1
proof=json.loads((here/'pattern-layout-build-validation.json').read_text());binary=(host.PRIVATE/'pattern-layout-probe219').read_bytes();assert hashlib.sha256(binary).hexdigest()==proof['sha256']
if w==2304:
 data=gzip.compress(binary,mtime=0);assert len(data)<=65536
 code="from pathlib import Path;import gzip,hashlib,sys;root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k219-runtime/boot-id-private.txt').read_bytes();p=Path('/run/samurai-camera219-probes/pattern-layout-probe');assert not p.exists();d=gzip.decompress(sys.stdin.buffer.read());assert hashlib.sha256(d).hexdigest()=="+repr(proof['sha256'])+";p.write_bytes(d);p.chmod(0o755)"
 host.ssh('python3 -c '+shlex.quote(code),input=data,timeout=30)
tag=f'pattern-layout-{w}x{h}'
code=(here/'native-mode-runner.py').read_text().replace("tag=f'{width}x{height}-{kind}-pattern{pattern}-{library}'",'tag='+repr(tag))
code=code.replace('/run/samurai-camera219-probes/native-mode-probe','/run/samurai-camera219-probes/pattern-layout-probe')
code=code.replace('report=dict(stage=219,','report=dict(stage=219,test_pattern_only=True,real_scene_cfa_not_inferred=True,')
compile(code,'native-layout219','exec')
p=host.ssh(f'python3 - raw 2 {w} {h} {cell} system',input=code.encode(),timeout=100)
(host.PRIVATE/(tag+'-host-private.log')).write_bytes(p.stdout+p.stderr)
r=json.loads(p.stdout);assert r['program_exit']==0 and len(r['frames'])==6
assert r['all_formats_restored'] and r['media_graph_restored'] and r['sensor_controls_restored'] and r['taint']==0 and not any(r['fault_delta'].values())
frames=r.pop('frames');values=frames[-1]['test_pattern_segment_phase4x4'];assert len(values)==128 and min(values)>=0
def spread(cell,dx,dy):
 worst=0
 for bar in range(8):
  groups={}
  for row in range(4):
   for col in range(4):groups.setdefault((((row+dy)//cell)%2,((col+dx)//cell)%2),[]).append(values[bar*16+row*4+col])
  worst=max(worst,max(max(g)-min(g) for g in groups.values()))
 return worst
fits={str(c):min(spread(c,dx,dy) for dx in range(4) for dy in range(4)) for c in [1,2]}
signatures=[''.join('1' if values[bar*16+phase]>511 else '0' for bar in range(8)) for phase in range(16)]
r.update(frame_count=6,phase_statistics_numeric_only=True,final_bar_phase_means=values,
 row_major_4x4_high_low_signatures=signatures,maximum_within_channel_spread_by_cell_size=fits,
 generated_pattern_best_cell_size=1 if fits['1']<0.1 and fits['2']>1 else 2 if fits['2']<0.1 and fits['1']>1 else None,
 real_scene_colour_filter_layout_not_accepted=True)
(here/(tag+'-validation.json')).write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({k:v for k,v in r.items() if k not in ['final_bar_phase_means']}))
