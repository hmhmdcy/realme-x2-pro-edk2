"""Retain linear DMA-BUFs for GTK CPU mmap, with GL/Vulkan disabled."""
from pathlib import Path
import ast
R=Path(__file__).resolve().parent
for stem in ['native','start','poll','analyze']:
 old=R/(stem+'-snapshot-cairo-r2.py');new=R/(stem+'-snapshot-mmap.py')
 s=old.read_text().replace('k240-snapshot-cairo-r2','k240-snapshot-mmap').replace('k240_snapshot_cairo_r2','k240_snapshot_mmap')
 s=s.replace('native-snapshot-cairo-r2.py','native-snapshot-mmap.py').replace('snapshot-cairo-r2-launch','snapshot-mmap-launch').replace('snapshot-cairo-r2-poll','snapshot-mmap-poll').replace('snapshot-cairo-r2-gui-logs','snapshot-mmap-gui-logs').replace('snapshot-cairo-r2-startup-validation','snapshot-mmap-startup-validation').replace('snapshot-cairo-r2-analysis-host','snapshot-mmap-analysis-host').replace('snapshot-cairo-r2-frame-flow-validation','snapshot-mmap-frame-flow-validation')
 s=s.replace('gl,vulkan,dmabuf,offload','gl,vulkan,offload')
 if stem=='native':
  s=s.replace("GSK_DEBUG='renderer',", "GSK_DEBUG='renderer',GDK_DEBUG='dmabuf',")
  s=s.replace('gpu_abort=False;trace=None;', 'gpu_abort=False;gpu_fds_seen=set();trace=None;')
  s=s.replace("observed=command(['dmesg'])", """for fd in Path('/proc',str(process.pid),'fd').glob('*'):
    try:target=os.readlink(fd)
    except OSError:continue
    if target.startswith('/dev/dri/'):gpu_fds_seen.add(target)
   observed=command(['dmesg'])""")
  s=s.replace("gtk_renderer='cairo',", "gtk_renderer='cairo',application_gpu_device_fds=sorted(gpu_fds_seen),")
 if stem=='analyze':
  s=s.replace("new=[x for x in lines if 'got new buffer' in x]", """new=[x for x in lines if 'got new buffer' in x]
mmap=[x for x in lines if 'Used mmap for downloading' in x]
textures=[x for x in lines if 'Created frame using' in x]
pts=[x for x in lines if 'pipewiresrc' in x and ('pts' in x.lower() or 'timestamp' in x.lower())]
errors=[x for x in lines if 'ERROR' in x or 'Bus Error' in x or 'Failed to transform frame' in x]""")
  s=s.replace('gtk4_preview_render_log_count=len(sinkrenders),', "gtk4_preview_render_log_count=len(sinkrenders),gtk_cpu_mmap_download_count=len(mmap),texture_creation_count=len(textures),application_bus_or_gst_error_count=len(errors),mmap_first3=mmap[:3],mmap_last3=mmap[-3:],texture_first3=textures[:3],pts_first3=pts[:3],pts_last3=pts[-3:],")
 ast.parse(s);new.write_text(s)
print('CPU mmap test prepared; native GTK4.24.1 advertises linear formats with GL/Vulkan disabled')
