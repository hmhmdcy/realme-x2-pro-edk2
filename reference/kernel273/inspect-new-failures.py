from pathlib import Path
import json
import host
code=r'''
from pathlib import Path
import json,subprocess
r=Path('/var/lib/samurai/k273-main-manual-r1');frames=json.loads((r/'stdout-private.json').read_text()).get('frames',[])
record=json.loads(Path('/run/samurai-ssc/state.json').read_text())
logs={str(p):p.read_text(errors='replace')[-50000:] for p in Path('/run/samurai-ssc').glob('*') if p.is_file() and p.name.endswith(('.log','.txt'))}
q=subprocess.run(['rc-service','--help'],capture_output=True,text=True)
print(json.dumps(dict(probe_stderr=(r/'stderr-private.log').read_text(errors='replace'),last_frames=[{k:v for k,v in f.items() if k not in ['raw','rgb']} for f in frames[-10:]],
 ssc_state={k:v for k,v in record.items() if k not in ['boot_id','daemon']},ssc_logs=logs,
 rc_service_help=q.stdout+q.stderr)))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=25);(host.PRIVATE/'new-failures-private.json').write_bytes(q.stdout);d=json.loads(q.stdout)
print('probe stderr tail','\n'.join(d['probe_stderr'].splitlines()[-8:]));print('last frames',json.dumps([{k:f[k] for k in ['queued_index','sequence','exposure_us','analogue_gain'] if k in f} for f in d['last_frames']]))
print('SSC state',json.dumps(d['ssc_state']));print('SSC log errors',json.dumps({p:[l for l in t.splitlines() if any(w in l.lower() for w in ['error','fail','timeout','fatal','no ','not ','refus'])][-8:] for p,t in d['ssc_logs'].items()}))
print('service nodeps options','\n'.join(l for l in d['rc_service_help'].splitlines() if 'deps' in l))
