"""Export retained fault receipts and summarize camera-specific diagnostics."""
from pathlib import Path
import json
import host
R=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import json,re
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
out=r/'k240-snapshot-fault-stop'
logs=json.loads((out/'camera-logs-private.json').read_text())
filtered={}
patterns=['snapshot','aperture','libcamera','pipeline handler','simple.cpp','software_isp','softwareisp','camerabin','pipewiresrc','no pipeline']
for name,text in logs.items():
 lines=[x for x in text.splitlines() if any(s in x.lower() for s in patterns)]
 filtered[Path(name).name]=lines[-100:]
dm=(out/'dmesg-private.txt').read_text()
gpu=[x for x in dm.splitlines() if 'gpu fault:' in x][-3:]
provider=json.loads((r/'k240-snapshot-provider/provider-stdout-private.json').read_text())
report=dict(observed=json.loads((r/'k240-snapshot-observed-stream/summary.json').read_text()),
 stop=json.loads((out/'summary.json').read_text()),logs=filtered,gpu_last3=gpu,
 provider_properties=[dict(display_name=x['display_name'],properties=x['properties']) for x in provider['devices']])
print(json.dumps(report))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=15)
(host.PRIVATE/'snapshot-failure-retained-private.json').write_bytes(p.stdout)
data=json.loads(p.stdout)
(R/'snapshot-existing-stream-validation.json').write_text(json.dumps(data['observed'],indent=2)+'\n')
print(json.dumps({k:v for k,v in data.items() if k not in ['observed','stop']}))
# Keep full capability strings private and make the public provider receipt concise.
p=R/'snapshot-provider-validation.json';report=json.loads(p.read_text())
(host.PRIVATE/'snapshot-provider-full-private.json').write_text(json.dumps(report,indent=2)+'\n')
for d in report['cameras']:
 caps=d.pop('caps',None);d['caps_structures']=len(caps.split(';')) if caps else 0
report['no_camera_stream_or_shutter']=True
report['probe_only_enumerated_devices']=True
report['external_snapshot_input_stream_observed']=True
p.write_text(json.dumps(report,indent=2)+'\n')
