from pathlib import Path
import json,xml.etree.ElementTree as ET
import host
R=Path(__file__).resolve().parent
ins=json.loads((host.PRIVATE/'gw1-contract-inspection-private.json').read_text())
direct={v:json.loads((host.PRIVATE.parent/'kernel270'/('gw1-'+v+'-direct-registers-private.json')).read_text()) for v in ['qtech','sunny']}
details=[]
for row in ins['variants']:
 v=row['variant'];data=direct[v]
 modes=[]
 for i,regs in enumerate(data['modes']):
  modes.append(dict(index=i,records=len(regs),non_scalar=[dict(address=hex(r['address']),operation=r['operation'],values=len(r['values']),first=r['values'][:6],last=r['values'][-6:]) for r in regs if len(r['values'])!=1 or r['operation']!='WRITE'],
   first=[dict(address=hex(x['address']),values=x['values'][:5]) for x in regs[:3]],last=[dict(address=hex(x['address']),values=x['values'][-5:]) for x in regs[-3:]]))
 details.append(dict(variant=v,slave_info=row['slave_info'],modes=modes,init_last=data['init'][-3:]))
report=dict(stage=272,slave_info_equal=ins['variants'][0]['slave_info']==ins['variants'][1]['slave_info'],
 init_equal=direct['qtech']['init']==direct['sunny']['init'],modes_equal=[a==b for a,b in zip(direct['qtech']['modes'],direct['sunny']['modes'])],details=details)
(host.PRIVATE/'gw1-contract-summary-private.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
