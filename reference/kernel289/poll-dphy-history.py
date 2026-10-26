"""Check the actual submitted worker identity and compare its LUT words with source."""
from pathlib import Path
import json,re,subprocess
import host

ROOT=Path(__file__).resolve().parent
identity=json.loads((host.PRIVATE/'dphy-launch-private.json').read_text())
code=r'''
from pathlib import Path
import json
r=Path('/var/lib/samurai/k289-dmi-r3');s=json.loads((r/'state-private.json').read_text());assert s['pid']==identity['pid']
p=Path('/proc',str(identity['pid']));live=False
if p.exists():
 fields=(p/'stat').read_text().rsplit(')',1)[1].split();live=fields[19]==identity['start_ticks'] and fields[0]!='Z'
print(json.dumps(dict(state=s,matching_worker_live=live,
 summary=json.loads((r/'summary-private.json').read_text()) if (r/'summary-private.json').exists() else None,
 failure=(r/'failure-private.txt').read_text() if (r/'failure-private.txt').exists() else None)))
'''
q=host.ssh('python3 -',input=('identity='+repr(identity)+'\n'+code).encode(),timeout=20)
data=json.loads(q.stdout);(host.PRIVATE/'dphy-poll-private.json').write_bytes(q.stdout)
print(json.dumps({k:v for k,v in data.items() if k!='summary'},indent=2))
if not data['summary']:raise SystemExit(0)
summary=data['summary'];(ROOT/'dphy-capture-validation.json').write_text(json.dumps(summary,indent=2)+'\n')
source=subprocess.check_output(['git','-C','/home/cy122/x2pro-linux/camera279-isp-kernel','show','HEAD:drivers/media/platform/qcom/camss/camss-vfe-175-gamma.c']).decode()
points=[int(x) for x in re.findall(r'\d+',source.split('vfe_175_gamma_srgb[VFE_175_GAMMA_POINTS] = {')[1].split('};')[0])];assert len(points)==65
expected=[points[i]|((points[i+1]-points[i])&1023)<<10 for i in range(64)]
tables=[]
for auto,selector,cfg,words,addr in re.findall(r'DMI_TABLE auto_inc=(\d+) selector=(\d+) cfg=([0-9a-f]+) words=([0-9a-f,]+) addr_after=([0-9a-f]+)',summary['tool_output']):
 values=[int(x,16) for x in words.split(',')];assert len(values)==64
 tables.append(dict(auto_inc=int(auto),selector=int(selector),cfg=int(cfg,16),addr_after=int(addr,16),
  matching_words=sum(a==b for a,b in zip(values,expected)),unique_words=len(set(values)),first_words=values[:8],last_words=values[-4:]))
report=dict(stage=289,tool_exit=summary['tool_exit'],frames=summary['actual_frames'],graph_restored=summary['graph_restored'],
 dmi_state_restored='DMI_END state_restored=1' in summary['tool_output'],expected_first_words=expected[:8],tables=tables,
 fault_delta=summary['fault_delta'],after=summary['after'])
(ROOT/'gamma-lut-dphy-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
