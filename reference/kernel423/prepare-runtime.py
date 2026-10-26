"""Stage a matching private IPA3/core/proxy and temporary profiles, no installation."""
from pathlib import Path
import ast,hashlib,importlib.util,json,shlex,sys,tarfile
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
attempt=sys.argv[1] if len(sys.argv)>1 else 'r1';assert attempt in ['r1','r2','r3']
for n in ['build-validation','ipa-validation','domains-validation','probe-validation','packet-validation','built-caller-validation']:
 assert json.loads((HERE/(n+'.json')).read_text())['passed'],n
if attempt=='r2':
 prior=json.loads((HERE/'runtime-r1-validation.json').read_text());assert prior['terminal'] and not any(prior[k] for k in ['worker_live','client_live','collector_live'])
 assert json.loads((HERE/'build-validation.json').read_text())['callers_forced_recompiled']
if attempt=='r3':assert json.loads((HERE/'runtime-r2-validation.json').read_text())['passed'] and json.loads((HERE/'roundtrip-validation.json').read_text())['passed']
s=importlib.util.spec_from_file_location('prefix395',HERE.parent/'kernel395/durable-prefix.py');prefix=importlib.util.module_from_spec(s);s.loader.exec_module(prefix)
worker=prefix.source().replace("'stage':395","'stage':423")+'\n'+(HERE/'runtime-worker-body.py').read_text();ast.parse(worker)
(P/'worker.py').write_text(worker)
files={'worker.py':P/'worker.py','capture':P/'capture','dump-collector.py':HERE.parent/'kernel420/dump-collector.py',
 'lib/libcamera.so.0.7.2':P/'libcamera.so.0.7.2','ipa/ipa_camss_vfe.so':P/'ipa_camss_vfe.so','ipa/ipa_camss_vfe.so.sign':P/'ipa_camss_vfe.so.sign','proxy/camss_ipa_proxy':P/'camss_ipa_proxy'}
for n in ['factory','gamma-roundtrip','colour-roundtrip','bypass']:files['profiles/'+n+'-s5kgw1-private.yaml']=P/(n+'-s5kgw1-private.yaml')
proof=json.loads((P.parent/'kernel420/install-proof-private.json').read_text())
normal={'/'+n:h for n,h in proof['installed_files'].items()};normal.update({i['target']:i['new_sha256'] for i in proof['driver_pair']})
captures=[dict(name='pattern-'+n,profile=n,pattern=2) for n in ['bypass','colour-roundtrip','gamma-roundtrip']] if attempt in ['r1','r2'] else [dict(name='pattern-factory',profile='factory',pattern=2),dict(name='scene-factory',profile='factory',pattern=0),dict(name='scene-factory-isolated',profile='factory',pattern=0,isolated=True)]
meta=dict(stage=423,attempt=attempt,normal_files=normal,profiles=proof['private_defaults'],captures=captures,payload_sha256={n:hashlib.sha256(p.read_bytes()).hexdigest() for n,p in files.items()})
(P/('manifest-'+attempt+'-private.json')).write_text(json.dumps(meta,indent=2)+'\n')
payload=P/('payload-'+attempt+'-private.tar.gz');assert not payload.exists()
with tarfile.open(payload,'w:gz') as tar:
 for n,p in files.items():tar.add(p,arcname=n,recursive=False)
root='/var/lib/samurai/k423-tone-'+attempt
code='''from pathlib import Path
import hashlib,json
root=Path(ROOT);assert not root.exists();meta=META
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k394-recovered/boot-id-private.txt').read_bytes()
assert all(hashlib.sha256(Path(n).read_bytes()).hexdigest()==h for n,h in meta['normal_files'].items())
root.mkdir(mode=0o700);print('Staging423: same boot guard and formal runtime verified.')
'''.replace('ROOT',repr(root)).replace('META',repr(meta))
print(host.ssh('python3 -c '+shlex.quote(code),timeout=25).stdout.decode())
s=importlib.util.spec_from_file_location('transport184',HERE.parent/'kernel184/host.py');transport=importlib.util.module_from_spec(s);s.loader.exec_module(transport)
q=transport.upload(payload,root+'/payload-private.tar.gz');(P/('upload-'+attempt+'-private.log')).write_bytes(q.stdout+q.stderr)
fixture=P.parent/'kernel363/pipeline-fixture'
code='''from pathlib import Path
import hashlib,json,os,shutil,tarfile
root=Path(ROOT);meta=META
assert hashlib.sha256((root/'payload-private.tar.gz').read_bytes()).hexdigest()==PAYLOAD
with tarfile.open(root/'payload-private.tar.gz','r:gz') as tar:
 assert all(m.isfile() and m.name in meta['payload_sha256'] for m in tar.getmembers())
 for m in tar.getmembers():
  p=root/m.name;p.parent.mkdir(parents=True,exist_ok=True)
  with p.open('xb') as f:f.write(tar.extractfile(m).read());f.flush();os.fsync(f.fileno())
for n,h in meta['payload_sha256'].items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==h
cached=Path('/var/lib/samurai/k420-install-r1/pipeline-fixture');assert hashlib.sha256(cached.read_bytes()).hexdigest()==FIXTURE
shutil.copyfile(cached,root/'pipeline-fixture')
for n in ['pipeline-fixture','capture','proxy/camss_ipa_proxy']:(root/n).chmod(0o700)
(root/'lib/libcamera.so.0.7').symlink_to('libcamera.so.0.7.2')
(root/'manifest.json').write_text(json.dumps(meta)+'\\n');(root/'stage-manifest-private.json').write_text(json.dumps(dict(files_sha256=meta['payload_sha256']))+'\\n')
print(json.dumps(dict(stage=423,staged=True,private_ipa_version=3,kernel_modules_not_changed=True,passed=True)))
'''.replace('ROOT',repr(root)).replace('META',repr(meta)).replace('PAYLOAD',repr(hashlib.sha256(payload.read_bytes()).hexdigest())).replace('FIXTURE',repr(hashlib.sha256(fixture.read_bytes()).hexdigest()))
q=host.ssh('python3 -c '+shlex.quote(code),timeout=35);(HERE/('staging-'+attempt+'-validation.json')).write_bytes(q.stdout);print(q.stdout.decode())
