from pathlib import Path
import ast,hashlib,io,json,shlex,sys,tarfile
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;action=sys.argv[1];remote='/var/lib/samurai/k430-control-r1';payload=None
if action=='launch':
 assert json.loads((HERE/'control-build-validation.json').read_text())['passed']
 prefix=(HERE.parent/'kernel342/native-install.py').read_text().split('def versions():')[0].replace("'stage':342","'stage':430")
 prefix=prefix.replace("marker.write_text(json.dumps(state,indent=2)+'\\n')", "tmp=root/'state.tmp';tmp.write_text(json.dumps(state,indent=2)+'\\n');tmp.replace(marker)")
 worker=prefix+'\n'+(HERE/'control-worker-body.py').read_text();ast.parse(worker)
 files={'worker.py':worker.encode(),**{n:(P/n).read_bytes() for n in ['control-ipe','full-private.bin','parameters-private.bin']}}
 meta=dict(normal_notes=json.loads((P.parent/'kernel429/runtime-collected-r4/state.json').read_text())['before_notes'],payload_sha256={n:hashlib.sha256(b).hexdigest() for n,b in files.items()})
 files['manifest.json']=json.dumps(meta).encode();stream=io.BytesIO()
 with tarfile.open(fileobj=stream,mode='w:gz') as tar:
  for n,b in files.items():m=tarfile.TarInfo(n);m.size=len(b);tar.addfile(m,io.BytesIO(b))
 payload=stream.getvalue()
 code='''from pathlib import Path
import hashlib,io,json,subprocess,sys,tarfile
root=Path(ROOT);assert not root.exists();root.mkdir(mode=0o700)
with tarfile.open(fileobj=io.BytesIO(sys.stdin.buffer.read()),mode='r:gz') as tar:
 for m in tar.getmembers():
  assert m.isfile() and m.name in NAMES
  (root/m.name).write_bytes(tar.extractfile(m).read())
meta=json.loads((root/'manifest.json').read_text())
for n,h in meta['payload_sha256'].items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==h
(root/'control-ipe').chmod(0o700)
with (root/'worker.log').open('xb') as log:child=subprocess.Popen(['python3',str(root/'worker.py'),str(root)],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
print(json.dumps(dict(launched=True,pid=child.pid)))
'''.replace('NAMES',repr(set(files)))
elif action=='observe':
 code='''from pathlib import Path
import json
root=Path(ROOT);s=json.loads((root/'state.json').read_text());print(json.dumps(s))
'''
elif action=='collect':
 code='''from pathlib import Path
import json,sys,tarfile
root=Path(ROOT);assert json.loads((root/'state.json').read_text())['terminal']
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|gz') as tar:
 for p in root.iterdir():
  if p.is_file():tar.add(p,arcname=p.name)
'''
else:raise ValueError(action)
q=host.ssh('python3 -c '+shlex.quote(code.replace('ROOT',repr(remote))),input=payload,timeout=35);q.check_returncode()
if action=='collect':
 out=P/'control-collected-r1';out.mkdir(exist_ok=True)
 with tarfile.open(fileobj=io.BytesIO(q.stdout),mode='r:gz') as tar:
  for m in tar.getmembers():
   dest=out/m.name;assert m.isfile() and dest.resolve().is_relative_to(out.resolve());dest.write_bytes(tar.extractfile(m).read())
 print('Collected private control outputs and logs')
else:
 (P/('control-'+action+'-private.json')).write_bytes(q.stdout);print(q.stdout.decode())
