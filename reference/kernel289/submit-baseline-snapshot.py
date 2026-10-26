"""Recheck the unchanged known helper and live registers after the failed readback."""
from pathlib import Path
import base64,json
import host

ROOT=Path(__file__).resolve().parent
base=(ROOT.parent/'kernel288/native-pix-tpg.py').read_text().split('save()\ntry:')[0]
body=(ROOT.parent/'kernel288/native-isolated-pix.py').read_text().split('save();child=None')[1]
worker=(base+'save();child=None'+body).replace('k288-tpg-r1','k289-baseline-r1')
worker=worker.replace('import json,os,re,signal,subprocess,time,traceback','import json,mmap,os,re,signal,struct,subprocess,time,traceback')
worker=worker.replace('stage=288','stage=289')
compile(worker,'baseline-worker','exec');(ROOT/'native-baseline-snapshot.py').write_text(worker)
code=r'''
from pathlib import Path
import base64,json,subprocess
r=Path('/var/lib/samurai');assert not (r/'k289-baseline-r1').exists()
script=r/'k289-tools/native-baseline-snapshot.py';assert not script.exists();script.write_bytes(base64.b64decode(WORKER))
with (r/'k289-tools/baseline-worker-private.log').open('xb') as log:
 p=subprocess.Popen(['python3',str(script)],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
print(json.dumps(dict(pid=p.pid,start_ticks=Path('/proc',str(p.pid),'stat').read_text().rsplit(')',1)[1].split()[19])))
'''.replace('WORKER',repr(base64.b64encode(worker.encode()).decode()))
assert not (host.PRIVATE/'baseline-launch-private.json').exists()
q=host.ssh('python3 -',input=code.encode(),timeout=20)
(host.PRIVATE/'baseline-launch-private.json').write_bytes(q.stdout);print(q.stdout.decode())
poll=(ROOT/'poll-dmi-readback.py').read_text().split('source=subprocess.check_output')[0]
poll=poll.replace('dmi-launch-private.json','baseline-launch-private.json').replace('k289-dmi-r1','k289-baseline-r1').replace('dmi-poll-private.json','baseline-poll-private.json').replace('dmi-capture-validation.json','baseline-capture-validation.json')
poll+='print(json.dumps(summary,indent=2))\n'
(ROOT/'poll-baseline-snapshot.py').write_text(poll)
