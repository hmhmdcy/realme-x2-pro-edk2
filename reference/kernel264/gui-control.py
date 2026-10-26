from pathlib import Path
import json,shlex,sys
import host
R=Path(__file__).parent;mode=sys.argv[1];assert mode in ['scan','capture']
args=' '+mode
if mode=='capture':
 d=json.loads((host.PRIVATE/'gui-scan-private.json').read_text());choices=[dict(e,action_index=i,action_name=a[0]) for e in d['entries'] for i,a in enumerate(e['actions']) if a[0]=='win.take-picture'];assert len(choices)==1,[(e['name'],e['role']) for e in d['entries'] if e['actions']]
 args+=' '+shlex.quote(json.dumps(choices[0]))
r=host.ssh('python3 -'+args,input=(R/'gui-control-native.py').read_bytes(),timeout=30,check=False);(host.PRIVATE/('gui-'+mode+'-private.json')).write_bytes(r.stdout);(host.PRIVATE/('gui-'+mode+'-stderr-private.log')).write_bytes(r.stderr)
assert r.returncode==0,'Inspect the private accessibility output'
d=json.loads(r.stdout)
if mode=='scan':print(json.dumps(dict(pid=d['pid'],buttons=[{k:e[k] for k in ['name','role','actions']} for e in d['entries'] if e['actions']]),indent=2))
else:print(json.dumps(dict(accessible_shutter_action_accepted=d['accessible_shutter_action_accepted'],jpeg_count=len(d['new_jpegs']),jpeg_bytes=[p['bytes'] for p in d['new_jpegs']],quit_action_sent=d['quit_action_sent']),indent=2))
