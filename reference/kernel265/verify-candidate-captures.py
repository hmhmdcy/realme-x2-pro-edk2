from pathlib import Path
import json
import host
R=Path(__file__).parent
code=r'''
from pathlib import Path
import json
root=Path('/var/lib/samurai');results=[]
for run in [7,8,9]:
 p=root/('k265-camera-'+str(run));d=json.loads((p/'summary.json').read_text());s=(p/'stderr-private.txt').read_text(errors='replace')
 assert json.loads((p/'state-private.json').read_text())['state']=='terminal'
 assert d['diagnostic_completed'] and d['runtime_logging_restored']
 q=d['probe_result'];errors=s.count('was not recycled')
 assert errors==0 and q['held_content_changed']==0 and q['held_pts_changed']==0 and q['application_copy_env'] is None and q['shared_bufferpool']
 assert len(q['shots'])==3 and q['source_plugin']=='/var/lib/samurai/k265-candidate/libgstpipewire.so'
 results.append(dict(run=run,camera=d['camera_selected'],held_checked=q['held_checked'],frames=q['buffers'],photos=len(q['shots']),recycle_errors=errors,held_changes=q['held_content_changed'],normal_release_clean=d['camera_devices_suspended'] and d['mclk1_mclk2_disabled'] and d['rails_unchanged'],runtime_logging_restored=d['runtime_logging_restored']))
print(json.dumps(dict(stage=265,isolated_candidate=True,system_not_deployed=True,runs=results,total_checks=sum(x['held_checked'] for x in results),total_photos=sum(x['photos'] for x in results)),indent=2))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=20);d=json.loads(q.stdout);(R/'candidate-capture-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(q.stdout.decode())

