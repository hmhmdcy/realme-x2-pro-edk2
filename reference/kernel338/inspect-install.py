"""Observe the existing install worker; collect its consumer results when terminal."""
from pathlib import Path
import json,re,shlex,sys
import host

HERE=Path(__file__).resolve().parent
name=sys.argv[1]
code='''
from pathlib import Path
import json
root=Path(ROOT);state=json.loads((root/'state.json').read_text())
p=Path('/proc',str(state['pid']),'stat')
live=p.exists() and p.read_text().rsplit(')',1)[1].split()[0]!='Z'
print(json.dumps(dict(state=state,worker_live=live,
 logs={p.name:p.read_text(errors='replace') for p in root.glob('*.log')},
 failures={p.name:p.read_text() for p in root.glob('*failure*')})))
'''.replace('ROOT',repr('/var/lib/samurai/k338-install-'+name))
q=host.raw_ssh('python3 -c '+shlex.quote(code),timeout=25)
(host.PRIVATE/('install-'+name+'-observation.json')).write_bytes(q.stdout)
d=json.loads(q.stdout)
if '--collect' not in sys.argv:
    print(json.dumps({k:d[k] for k in ['state','worker_live','failures']},indent=2))
    raise SystemExit(0)
assert d['state']['terminal'] and not d['worker_live'],'Worker is still live'
summary=d['state']['summary']
gst=re.search(r'GST_RESULT frames=(\d+) width=(\d+) height=(\d+) bus-errors=(\d+) result=(\d+)',d['logs'].get('installed-gstreamer.log',''))
pw=re.search(r'PW_RESULT frames=(\d+) format-accepted=(\d+) errors=(\d+) result=(\d+)',d['logs'].get('installed-pipewire.log',''))
report=dict(stage=338,run=name,transaction=summary,
    hardware_cameras=d['logs'].get('enumeration.log','').count('for pipeline handler camss-vfe'),
    pipewire_camera_nodes=len(re.findall(r'PW_NODE id=',d['logs'].get('pw-enumeration.log',''))),
    gstreamer=dict(frames=int(gst[1]),width=int(gst[2]),height=int(gst[3]),errors=int(gst[4]),result=int(gst[5])) if gst else None,
    pipewire=dict(frames=int(pw[1]),format_accepted=bool(int(pw[2])),errors=int(pw[3]),result=int(pw[4])) if pw else None)
proof=json.loads((host.PRIVATE/'install-proof.json').read_text())
report['tested_module_loaded']=summary['loaded_camss_note_sha256']==proof['module_note_sha256']
report['passed']=bool(summary['passed'] and report['tested_module_loaded'] and
    report['hardware_cameras']==4 and report['pipewire_camera_nodes']==4 and gst and pw and
    int(gst[1])>0 and not int(gst[4]) and not int(gst[5]) and int(pw[1])>0 and int(pw[2]) and not int(pw[3]) and not int(pw[4]))
(HERE/('install-'+name+'-validation.json')).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
raise SystemExit(0 if report['passed'] else 1)
