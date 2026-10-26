"""Reuse deployed r26 IPA and the existing internal-pattern capture fixture."""
from pathlib import Path
import io, json, shlex, tarfile
import host
HERE=Path(__file__).resolve().parent
code=r"""
from pathlib import Path
import json,subprocess
print(json.dumps({'kernel':subprocess.check_output(['uname','-r']).decode().strip(),
'versions':{d['P']:d['V'] for entry in Path('/lib/apk/db/installed').read_text().split('\n\n') if (d:=dict(line.split(':',1) for line in entry.splitlines() if ':' in line)).get('P') in ['libcamera','samurai-camera-config']},
'platforms':{n:Path('/sys/bus/platform/devices',n,'power/runtime_status').read_text().strip() for n in ['acb3000.camss','ac4a000.cci','ac4b000.cci']},
'taint':int(Path('/proc/sys/kernel/tainted').read_text())}))
"""
q=host.raw_ssh('python3 -c '+shlex.quote(code),timeout=20)
state=json.loads(q.stdout);assert state['taint']==0 and all(v=='suspended' for v in state['platforms'].values())
assert state['versions']['libcamera']=='99990.7.2-r26'
(host.PRIVATE/'preflight.json').write_text(json.dumps(state,indent=2)+'\n')
s=(HERE.parent/'kernel321/native-probe.py').read_text().replace('stage=321','stage=322')
s=s.replace('Temporarily load the new CAMSS, capture RGB, then restore the deployed module.','Capture factory/unit LSC using installed IPA, then restore consumers and media state.')
s=s.replace("env=dict(os.environ,LIBCAMERA_IPA_MODULE_PATH=str(root/'ipa'),","env=dict(os.environ,")
s=s.replace("'LIBCAMERA_IPA_FORCE_ISOLATION']","'LIBCAMERA_IPA_FORCE_ISOLATION','LIBCAMERA_IPA_MODULE_PATH']")
(HERE/'native-probe.py').write_text(s)
files={'worker.py':HERE/'native-probe.py','pipeline-fixture':host.PRIVATE.parent/'kernel313/pipeline-fixture',
 'bin/lsc-smoke':Path('/home/cy122/x2pro-linux/libcamera214-root/private/camss321-runtime/lsc-smoke')}
for p in (host.PRIVATE/'profiles').glob('*.yaml'):files['profiles/'+p.name]=p
with tarfile.open(host.PRIVATE/'probe.tar.gz','w:gz') as tar:
 for name,p in files.items():
  raw=p.read_bytes();item=tarfile.TarInfo(name);item.size=len(raw);item.mode=0o700 if name.startswith('bin/') or name=='pipeline-fixture' else 0o600;tar.addfile(item,io.BytesIO(raw))
for name in ['launch-probe.py','poll-probe.py','fetch-results.py']:
 s=(HERE.parent/'kernel321'/name).read_text().replace('k321-lsc-','k322-lsc-');(HERE/name).write_text(s)
print(json.dumps(state,indent=2));print('Prepared temporary profiles; using installed signed IPA.')
