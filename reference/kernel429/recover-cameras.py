"""Revalidate the formal four-camera stack after the verified physical restart."""
from pathlib import Path
import ast,base64,hashlib,io,json,shlex,sys,tarfile
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
root='/var/lib/samurai/k429-camera-recovery-r1'
action=sys.argv[1];payload=None
assert json.loads((HERE/'postboot-validation.json').read_text())['passed']
if action=='launch':
 prefix=(HERE.parent/'kernel342/native-install.py').read_text().split('def versions():')[0].replace("'stage':342","'stage':429")
 prefix=prefix.replace("marker.write_text(json.dumps(state,indent=2)+'\\n')", "tmp=root/'state.tmp';tmp.write_text(json.dumps(state,indent=2)+'\\n');tmp.replace(marker)")
 body=(HERE.parent/'kernel394/recovery-worker-body.py').read_text().replace('/var/lib/samurai/k394-recovered/boot-id-private.txt','/var/lib/samurai/k429-recovered/boot-id-private.txt')
 worker=prefix+'\n'+body;ast.parse(worker)
 collector=(HERE.parent/'kernel391/dump-collector.py').read_text().replace('start<600','start<240').replace('start>=600','start>=240').replace('/var/lib/samurai/k390-active/boot-id-private.txt','/var/lib/samurai/k429-recovered/boot-id-private.txt')
 baseline=json.loads((P/'pre-reboot-private.json').read_text())
 meta={'normal_files':{r['path']:r['sha256'] for r in baseline['formal_disk_modules'].values()}}
 fixture=P.parent/'kernel363/pipeline-fixture'
 files={'worker.py':worker.encode(),'dump-collector.py':collector.encode(),'pipeline-fixture':fixture.read_bytes()}
 meta['payload_sha256']={n:hashlib.sha256(b).hexdigest() for n,b in files.items()}
 payload_io=io.BytesIO()
 files['manifest.json']=(json.dumps(meta)+'\n').encode()
 with tarfile.open(fileobj=payload_io,mode='w:gz') as tar:
  for n,b in files.items():
   m=tarfile.TarInfo(n);m.size=len(b);tar.addfile(m,io.BytesIO(b))
 payload=payload_io.getvalue()
 code='''from pathlib import Path
import hashlib,io,json,os,subprocess,sys,tarfile
root=Path(ROOT);assert not root.exists();root.mkdir(mode=0o700)
with tarfile.open(fileobj=io.BytesIO(sys.stdin.buffer.read()),mode='r:gz') as tar:
 for m in tar.getmembers():
  assert m.isfile() and m.name in ['worker.py','dump-collector.py','pipeline-fixture','manifest.json']
  (root/m.name).write_bytes(tar.extractfile(m).read())
meta=json.loads((root/'manifest.json').read_text())
for n,h in meta['payload_sha256'].items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==h
(root/'pipeline-fixture').chmod(0o700);(root/'manifest.json').write_text(json.dumps(meta)+'\\n')
with (root/'worker.log').open('xb') as log:
 child=subprocess.Popen(['python3',str(root/'worker.py'),str(root)],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
(root/'launch-private.json').write_text(json.dumps(dict(pid=child.pid))+'\\n');print(json.dumps(dict(launched=True,pid=child.pid)))
'''
elif action=='observe':
 code='''from pathlib import Path
import json
root=Path(ROOT);state=json.loads((root/'state.json').read_text());p=Path('/proc',str(state['pid']))
live=p.exists() and (p/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z'
print(json.dumps(dict(state=state,worker_live=live)))
'''
elif action=='collect':
 code='''from pathlib import Path
import json,sys,tarfile
root=Path(ROOT);assert json.loads((root/'state.json').read_text())['terminal']
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|gz') as tar:
 for p in root.rglob('*'):
  if p.is_file():tar.add(p,arcname=str(p.relative_to(root)))
'''
else:raise ValueError(action)
q=host.ssh('python3 -c '+shlex.quote(code.replace('ROOT',repr(root))),input=payload,timeout=35);q.check_returncode()
if action=='collect':
 out=P/'camera-recovery-collected';out.mkdir(exist_ok=True)
 with tarfile.open(fileobj=io.BytesIO(q.stdout),mode='r:gz') as tar:
  for m in tar.getmembers():
   target=out/m.name;assert m.isfile() and target.resolve().is_relative_to(out.resolve());target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(tar.extractfile(m).read())
 s=json.loads((out/'state.json').read_text());assert s['terminal']
 report={k:s[k] for k in ['captures','after','core_after','taint','new_unexpected_faults','normal_files_unchanged','test_knob_absent','passed'] if k in s}
 report.update(stage=429,physical_restart_verified=True,services_restored=all(len(v)==1 for v in s['services'].values()),after_status=s.get('after'),taint_after=s['taint'])
 (HERE/'camera-recovery-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
else:
 (P/('camera-recovery-'+action+'-private.json')).write_bytes(q.stdout);print(q.stdout.decode())
