from pathlib import Path
import json,sys
import host
mode=int(sys.argv[1])
code=r'''
from pathlib import Path
import json,re,sys
mode=int(sys.argv[1]);root=Path('/var/lib/samurai/k264-user')/('isolated-'+str(mode));events={}
for name in ['pipewire-private.log','wireplumber-private.log']:
 lines=(root/name).read_text(errors='replace').splitlines()
 events[name]=[l for l in lines if 'rebuild camera pool' in l or 'starting camera ' in l or 'stopping camera ' in l]
victim=root/'crash-client-stderr-private.txt'
wp=(root/'wireplumber-private.log').read_text()
all_logs=wp+'\n'+(root/'pipewire-private.log').read_text()
report=dict(mode=mode,events=events,output_io_before_start=[dict(status=int(a),buffer_id=int(b)) for a,b in re.findall(r'reset output IO before start status:(-?\d+) id:(\d+)',wp)],mix_io_before_bind=[dict(status=int(a),buffer_id=int(b)) for a,b in re.findall(r'reset camera mix IO status:(-?\d+) id:(\d+)',all_logs)],victim_buffers_before_sigkill=victim.read_text().count('got new buffer') if victim.exists() else None,result=json.loads((root/'summary.json').read_text()))
print(json.dumps(report))
'''
r=host.ssh('python3 - '+str(mode),input=code.encode());(host.PRIVATE/('analysis-'+str(mode)+'-private.json')).write_bytes(r.stdout)
d=json.loads(r.stdout)
# Public counts omit raw log timestamps/pointers; raw evidence remains private.
report=dict(mode=mode,rebuild_messages={name:sum('rebuild camera pool' in l for l in lines) for name,lines in d['events'].items()},start_messages=sum('starting camera ' in l for lines in d['events'].values() for l in lines),stop_messages=sum('stopping camera ' in l for lines in d['events'].values() for l in lines),output_io_before_start=d['output_io_before_start'],mix_io_before_bind=d['mix_io_before_bind'],victim_buffers_before_sigkill=d['victim_buffers_before_sigkill'],result=d['result'])
(Path(__file__).parent/('flow-'+str(mode)+'-validation.json')).write_text(json.dumps(report,indent=2)+'\n')
brief={k:v for k,v in report.items() if k!='result'};brief['clients']=[{k:r[k] for k in ['label','buffers','held_checked','held_content_changed','pts_strictly_increasing','not_recycled_errors']} for r in d['result']['clients']];brief['failure']=d['result']['failure'];print(json.dumps(brief,indent=2))
