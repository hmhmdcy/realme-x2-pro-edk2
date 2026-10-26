"""Read native sensor controls and the actual processing diagnostics without capturing."""
from pathlib import Path
import json,re
import host
R=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import json,subprocess
nodes={p.name:(p/'name').read_text().strip() for p in Path('/sys/class/video4linux').glob('v4l-subdev*')}
which=next(n for n,label in nodes.items() if label.startswith('s5k3m5 '))
logs={}
for name in ['raw-stderr-private.log','rgb-stderr-private.log','raw-stdout-private.log','rgb-stdout-private.log']:
 p=Path('/var/lib/samurai/k270-telephoto-capture-r1')/name
 if p.is_file():logs[name]=p.read_text(errors='replace')[-15000:]
for which_cam in ['wide','tele']:
 p=Path('/var/lib/samurai/k270-two-rear-jpeg-r1')/(which_cam+'-stderr-private.log')
 if p.is_file():logs[p.name]=p.read_text(errors='replace')[-20000:]
report=dict(controls=subprocess.check_output(['v4l2-ctl','-d','/dev/'+which,'--list-ctrls'],text=True),
 cam_help=subprocess.run(['cam','--help'],capture_output=True,text=True).stdout,
 libcamera_controls=subprocess.run(['cam','-c','/base/soc@0/cci@ac4b000/i2c-bus@0/camera@2d','--list-controls'],capture_output=True,text=True,timeout=15).stdout,
 logs=logs,
 patterns={label:subprocess.check_output(['v4l2-ctl','-d','/dev/'+n,'--get-ctrl=test_pattern'],text=True) for n,label in nodes.items() if label.startswith(('imx319 ','imx471 ','s5k3m5 ','msm_csid'))})
print(json.dumps(report))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=30)
(host.PRIVATE/'telephoto-controls-private.json').write_bytes(q.stdout);d=json.loads(q.stdout)
print(d['controls']);print(d['libcamera_controls']);print(d['cam_help'][:3500])
for name,log in d['logs'].items():
 print(name+'\n'+'\n'.join(l for l in log.splitlines() if re.search(r'warn|error|helper|sensor|expos|gain|black|ipa|configuration|stream',l,re.I))[-4500:])
print(json.dumps(d['patterns'],indent=2))
