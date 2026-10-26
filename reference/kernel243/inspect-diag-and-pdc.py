"""Read back PDC receipts and exposed diagnostic channels; no modem writes."""
from pathlib import Path
import json
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
p=r/'k243-pdc-readonly';results={x.stem:json.loads(x.read_text()) for x in p.glob('*-private.json')}
old={}
for name in ['k207-pdc-queries','k207-pdc-queries-r2','k207-pdc-readonly','k207-pdc-details']:
 q=r/name
 if q.is_dir():old[name]={x.name:json.loads(x.read_text()) for x in q.glob('*selected*json')}
rpmsg=[]
for p in Path('/sys/bus/rpmsg/devices').glob('*'):
 rpmsg.append(dict(name=p.name,path=str(p.resolve()),channel=(p/'name').read_text().strip() if (p/'name').exists() else None,driver=str((p/'driver').resolve()) if (p/'driver').exists() else None))
report=dict(stage=243,read_only=True,pdc_receipt_files=len(results),historical_contexts_found=len(old),rpmsg_devices=len(rpmsg),diag_channels=[dict(name=x['channel'],bound=x['driver'] is not None) for x in rpmsg if 'diag' in (x['channel'] or '').lower()])
print(json.dumps(dict(report=report,private=dict(pdc=results,historical=old,rpmsg=rpmsg))))
