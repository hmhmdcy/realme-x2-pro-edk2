from pathlib import Path
import json
import host
R=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import json,subprocess,time
device=Path('/sys/bus/i2c/devices/6-0072');sensor=Path('/sys/bus/i2c/devices/6-0010')
assert (device/'driver').resolve().name=='lc898219xi'
node=next('/dev/'+p.name for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().strip()=='lc898219xi 6-0072')
runtime_before=(device/'power/runtime_status').read_text().strip();q=subprocess.run(['v4l2-ctl','-d',node,'--list-ctrls'],capture_output=True,text=True,timeout=10);time.sleep(.2)
media=subprocess.check_output(['media-ctl','-p'],text=True)
print(json.dumps(dict(stage=275,node=node,driver=(device/'driver').resolve().name,compatible=(device/'of_node/compatible').read_bytes().decode().rstrip('\0'),runtime_before=runtime_before,runtime_after=(device/'power/runtime_status').read_text().strip(),control_exit=q.returncode,controls=q.stdout,stderr=q.stderr,
 sensor_lens_focus=(sensor/'of_node/lens-focus').read_bytes().hex(),lens_phandle=(device/'of_node/phandle').read_bytes().hex(),old_sensor_afvdd_absent=not (sensor/'of_node/afvdd-supply').exists(),media_graph=media)))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=20);(host.PRIVATE/'lens-initial-private.json').write_bytes(q.stdout);d=json.loads(q.stdout);graph=d.pop('media_graph')
assert d['sensor_lens_focus']==d['lens_phandle'] and d['old_sensor_afvdd_absent'] and d['control_exit']==0 and 'focus_absolute' in d['controls']
d['ancillary_graph_mentions_lens']='lc898219xi 6-0072' in graph
(R/'lens-initial-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
print('\n'.join(l for l in graph.splitlines() if any(s in l for s in ['lc898219','s5kgw1','ANCILLARY'])))
