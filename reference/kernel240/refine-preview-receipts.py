"""Recompute source PTS and distinguish preview errors from buffer ownership errors."""
from pathlib import Path
import json
import host
R=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import json,re,statistics
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
reports={}
for name in ['k240-snapshot-cairo','k240-snapshot-cairo-r2','k240-snapshot-mmap','k240-snapshot-mmap-r2']:
 p=r/name;d=json.loads((p/'frame-flow-analysis.json').read_text())
 text=(p/'stderr-private.txt').read_text(errors='replace')+'\n'+(p/'stdout-private.json').read_text(errors='replace')
 pts=[int(x) for x in re.findall(r'pipewiresrc[^\n]* pts (\d+), dts_offset',text)]
 gaps=[b-a for a,b in zip(pts,pts[1:])]
 report=dict(stage=240,context=name,pipewire_new_buffers=d['pipewire_new_buffer_count'],
  source_pts_count=len(pts),source_pts_strictly_increasing=bool(pts) and all(g>0 for g in gaps),
  source_pts_span_seconds=round((pts[-1]-pts[0])/1e9,6) if len(pts)>1 else None,
  source_median_pts_gap_ms=round(statistics.median(gaps)/1e6,6) if gaps else None,
  keepalive_log_count=d['pipewire_keepalive_log_count'],sink_render_calls=d['gtk4_preview_render_log_count'],
  cpu_mmap_downloads=text.count('Used mmap for downloading'),
  actual_gtk_cairo_renderer_logged="Using renderer 'GskCairoRenderer'" in text,
  actual_mmap_dimensions_1920x1080_linear_xr24='Used mmap for downloading 1920x1080 dmabuf (format XR24:0)' in text,
  paintable_bus_errors=text.count('Bus Error from'),frame_texture_conversion_failures=text.count('Failed to transform frame into textures'),
  pipewire_buffer_not_recycled_errors=text.count('was not recycled'),pending_frame_warnings=text.count('Have too many pending frames'),
  kernel_v4l2_trace_empty=not any(d['kernel_buffer_events'].values()),
  no_kernel_trace_frame_count_claim=True,source_buffer_pool_setting_unchanged=True,
  startup=d['startup'],scene_optical_colour_acceptance=False,photography_and_camera_switch_acceptance=False)
 (p/'refined-preview-analysis.json').write_text(json.dumps(report,indent=2)+'\n');reports[name]=report
print(json.dumps(reports))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=20)
(host.PRIVATE/'preview-refined-private.json').write_bytes(p.stdout)
data=json.loads(p.stdout)
for name,d in data.items():
 leaf=name.removeprefix('k240-')+'-frame-flow-validation.json'
 (R/leaf).write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps({k:{x:d[x] for x in ['source_pts_count','source_pts_strictly_increasing','source_pts_span_seconds','cpu_mmap_downloads','paintable_bus_errors','pipewire_buffer_not_recycled_errors']} for k,d in data.items()}))
