"""Check the actual submitted worker identity and compare its LUT words with source."""
from pathlib import Path
import json,re,subprocess
import host

ROOT=Path(__file__).resolve().parent
identity=json.loads((host.PRIVATE/'cst-response-launch-private.json').read_text())
code=r'''
from pathlib import Path
import json
r=Path('/var/lib/samurai/k290-response-r1');s=json.loads((r/'state-private.json').read_text());assert s['pid']==identity['pid']
p=Path('/proc',str(identity['pid']));live=False
if p.exists():
 fields=(p/'stat').read_text().rsplit(')',1)[1].split();live=fields[19]==identity['start_ticks'] and fields[0]!='Z'
print(json.dumps(dict(state=s,matching_worker_live=live,
 summary=json.loads((r/'summary-private.json').read_text()) if (r/'summary-private.json').exists() else None,
 failure=(r/'failure-private.txt').read_text() if (r/'failure-private.txt').exists() else None)))
'''
q=host.ssh('python3 -',input=('identity='+repr(identity)+'\n'+code).encode(),timeout=20)
data=json.loads(q.stdout);(host.PRIVATE/'cst-response-poll-private.json').write_bytes(q.stdout)
print(json.dumps({k:v for k,v in data.items() if k!='summary'},indent=2))
if not data['summary']:raise SystemExit(0)
summary=data['summary'];(ROOT/'cst-response-capture-validation.json').write_text(json.dumps(summary,indent=2)+'\n')
configs={}
for phase,kind,value,offset,clamp,full_y,full_c in re.findall(r'RESPONSE_CONFIG phase=(\d+) kind=(\w+) value=(\d+) cst_offset=([0-9a-f]+) cst_clamp=([0-9a-f]+) full_y=([0-9a-f]+) full_c=([0-9a-f]+)',summary['tool_output']):
 configs[int(phase)]=dict(phase=int(phase),kind=kind,value=int(value),offset=offset,clamp=clamp,full_y=full_y,full_c=full_c)
phases=[]
for row in re.findall(r'RESPONSE_MEASURE phase=(\d+) y_sum=(\d+) y_min=(\d+) y_max=(\d+) u_sum=(\d+) u_min=(\d+) u_max=(\d+) v_sum=(\d+) v_min=(\d+) v_max=(\d+)',summary['tool_output']):
 n,ys,yn,yx,us,un,ux,vs,vn,vx=map(int,row)
 phases.append(dict(configs[n],y=dict(mean=ys/76800,min=yn,max=yx),u=dict(mean=us/19200,min=un,max=ux),v=dict(mean=vs/19200,min=vn,max=vx)))
report=dict(stage=290,tool_exit=summary['tool_exit'],frames=summary['actual_frames'],phases=phases,
 graph_restored=summary['graph_restored'],fault_delta=summary['fault_delta'],after=summary['after'],
 registers_restored='RESPONSE_RESTORE registers=1' in summary['tool_output'] and 'GAMMA_RESTORE registers=1' in summary['tool_output'],
 inactive_gamma_lut_restore_readback_words=192 if 'GAMMA_RESTORE_LUT matching_words=192 expected=192' in summary['tool_output'] else 0)
(ROOT/'cst-response-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
