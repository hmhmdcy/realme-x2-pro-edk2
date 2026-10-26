from pathlib import Path
import json,sys
import host
assert sys.argv[1:] in [['raw'],['rgb']];kind=sys.argv[1]
R=Path(__file__).resolve().parent;dimensions='2304 1728' if kind=='raw' else '2296 1728'
r=host.ssh('python3 - '+kind+' 0 '+dimensions+' 1 system',input=(R/'native-front-regression.py').read_bytes(),timeout=75)
(host.PRIVATE/(kind+'-front-regression-host-private.log')).write_bytes(r.stdout+r.stderr)
report=json.loads(r.stdout);(R/(kind+'-front-regression-validation.json')).write_text(json.dumps(report,indent=2)+'\n')
assert report['program_exit']==0 and len(report['frames'])==6 and all(not f['all_zero'] for f in report['frames'])
assert report['all_formats_restored'] and report['media_graph_restored'] and report['sensor_controls_restored'] and report['camera_devices_suspended']
assert report['taint']==0 and not any(report['fault_delta'].values())
print(json.dumps(dict(stage=233,kind=kind,frames=len(report['frames']),all_nonzero=True,
 mean_range=[min(f['mean'] for f in report['frames']),max(f['mean'] for f in report['frames'])],
 controls_graph_formats_pm_restored=True,taint=0,fault_delta=report['fault_delta'],scene_images_saved=False)))
