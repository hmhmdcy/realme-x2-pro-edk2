from pathlib import Path
import host,json,sys

here=Path(__file__).resolve().parent
assert len(sys.argv)==7
kind,pattern,width,height,cell,library=sys.argv[1:]
assert kind in ['raw','rgb'] and pattern in ['0','2'] and width.isdigit() and height.isdigit() and cell in ['1','2'] and library in ['system','candidate']
tag=f'{width}x{height}-{kind}-pattern{pattern}-{library}'
command='python3 /run/samurai-camera219-probes/mode-runner.py '+' '.join(sys.argv[1:])
p=host.ssh(command,timeout=90)
(host.PRIVATE/(tag+'-host-private.log')).write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout)
(here/(tag+'-validation.json')).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='frames'}))
assert report['program_exit']==0 and report['stream_geometry']['width']==int(width) and report['stream_geometry']['height']==int(height)
assert report['all_formats_restored'] and report['media_graph_restored'] and report['sensor_controls_restored'] and not report['restore_errors']
assert report['camera_devices_suspended'] and report['taint']==0 and not any(report['fault_delta'].values())
assert len(report['frames'])==6
if kind=='raw' or pattern!='0':assert all(not f['all_zero'] for f in report['frames'])
if kind=='raw' and pattern=='0':assert all(f['stddev']>0 and f['changed_fraction']>0 for f in report['frames'][1:])
if kind=='rgb' and pattern=='0':
    raw=json.loads((here/(f'{width}x{height}-raw-pattern0-system-validation.json')).read_text())
    positive=json.loads((here/(f'{width}x{height}-rgb-pattern2-candidate-validation.json')).read_text())
    assert all(f['stddev']>0 and f['changed_fraction']>0 for f in raw['frames'][1:]) and all(not f['all_zero'] for f in positive['frames'])
