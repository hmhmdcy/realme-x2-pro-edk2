"""Stage corrected IPA and a real AF/auto-tone probe, using verified cached unchanged helpers."""
from pathlib import Path
import ast,hashlib,importlib.util,json,shlex,sys,tarfile
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;root='/var/lib/samurai/k424-tone-r1'
for n in ['build','ipa','profile','packet','capture']:assert json.loads((HERE/(n+'-validation.json')).read_text())['passed'],n
s=importlib.util.spec_from_file_location('prefix395',HERE.parent/'kernel395/durable-prefix.py');prefix=importlib.util.module_from_spec(s);s.loader.exec_module(prefix)
worker=prefix.source().replace("'stage':395","'stage':424")+'\n'+(HERE.parent/'kernel423/runtime-worker-body.py').read_text();ast.parse(worker);(P/'worker.py').write_text(worker)
uploaded={'worker.py':P/'worker.py','capture':P/'capture','dump-collector.py':HERE.parent/'kernel420/dump-collector.py',
 'ipa/ipa_camss_vfe.so':P/'ipa_camss_vfe.so','ipa/ipa_camss_vfe.so.sign':P/'ipa_camss_vfe.so.sign',
 'profiles/factory-s5kgw1-private.yaml':P.parent/'kernel423/factory-s5kgw1-private.yaml'}
cached={'lib/libcamera.so.0.7.2':dict(path='/var/lib/samurai/k423-tone-r3/lib/libcamera.so.0.7.2',sha256=hashlib.sha256((P/'libcamera.so.0.7.2').read_bytes()).hexdigest()),
 'proxy/camss_ipa_proxy':dict(path='/var/lib/samurai/k423-tone-r3/proxy/camss_ipa_proxy',sha256=hashlib.sha256((P/'camss_ipa_proxy').read_bytes()).hexdigest()),
 'pipeline-fixture':dict(path='/var/lib/samurai/k420-install-r1/pipeline-fixture',sha256=hashlib.sha256((P.parent/'kernel363/pipeline-fixture').read_bytes()).hexdigest())}
proof=json.loads((P.parent/'kernel420/install-proof-private.json').read_text());normal={'/'+n:h for n,h in proof['installed_files'].items()};normal.update({i['target']:i['new_sha256'] for i in proof['driver_pair']})
captures=[dict(name='scene-factory-af',profile='factory',pattern=0),dict(name='scene-factory-af-isolated',profile='factory',pattern=0,isolated=True)]
meta=dict(stage=424,normal_files=normal,profiles=proof['private_defaults'],captures=captures,payload_sha256={**{n:hashlib.sha256(p.read_bytes()).hexdigest() for n,p in uploaded.items()},**{n:v['sha256'] for n,v in cached.items()}})
(P/'manifest-r1-private.json').write_text(json.dumps(meta,indent=2)+'\n');payload=P/'payload-r1-private.tar.gz';assert not payload.exists()
with tarfile.open(payload,'w:gz') as tar:
 for n,p in uploaded.items():tar.add(p,arcname=n,recursive=False)
code='''from pathlib import Path
import hashlib,json
root=Path(ROOT);assert not root.exists();meta=META
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k394-recovered/boot-id-private.txt').read_bytes()
old=Path('/var/lib/samurai/k423-tone-r3');state=json.loads((old/'state.json').read_text());assert state['terminal'] and state['passed']
for name,v in CACHED.items():assert hashlib.sha256(Path(v['path']).read_bytes()).hexdigest()==v['sha256']
assert all(hashlib.sha256(Path(n).read_bytes()).hexdigest()==h for n,h in meta['normal_files'].items())
root.mkdir(mode=0o700);print('Same guard, cached core/proxy/fixture and formal runtime verified; staging424 created.')
'''.replace('ROOT',repr(root)).replace('META',repr(meta)).replace('CACHED',repr(cached))
print(host.ssh('python3 -c '+shlex.quote(code),timeout=25).stdout.decode())
s=importlib.util.spec_from_file_location('transport184',HERE.parent/'kernel184/host.py');transport=importlib.util.module_from_spec(s);s.loader.exec_module(transport)
q=transport.upload(payload,root+'/payload-private.tar.gz');(P/'upload-r1-private.log').write_bytes(q.stdout+q.stderr)
code='''from pathlib import Path
import hashlib,json,os,shutil,tarfile
root=Path(ROOT);meta=META
assert hashlib.sha256((root/'payload-private.tar.gz').read_bytes()).hexdigest()==PAYLOAD
with tarfile.open(root/'payload-private.tar.gz','r:gz') as tar:
 assert all(m.isfile() and m.name in meta['payload_sha256'] for m in tar.getmembers())
 for m in tar.getmembers():
  p=root/m.name;p.parent.mkdir(parents=True,exist_ok=True)
  with p.open('xb') as f:f.write(tar.extractfile(m).read());f.flush();os.fsync(f.fileno())
for n,v in CACHED.items():
 source=Path(v['path']);assert hashlib.sha256(source.read_bytes()).hexdigest()==v['sha256'];p=root/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,p)
for n,h in meta['payload_sha256'].items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==h
for n in ['pipeline-fixture','capture','proxy/camss_ipa_proxy']:(root/n).chmod(0o700)
(root/'lib/libcamera.so.0.7').symlink_to('libcamera.so.0.7.2');(root/'manifest.json').write_text(json.dumps(meta)+'\\n')
(root/'stage-manifest-private.json').write_text(json.dumps(dict(files_sha256=meta['payload_sha256']))+'\\n')
print(json.dumps(dict(stage=424,staged=True,private_ipa_version=3,unchanged_helpers_verified_and_reused=True,kernel_modules_not_changed=True,passed=True)))
'''.replace('ROOT',repr(root)).replace('META',repr(meta)).replace('CACHED',repr(cached)).replace('PAYLOAD',repr(hashlib.sha256(payload.read_bytes()).hexdigest()))
q=host.ssh('python3 -c '+shlex.quote(code),timeout=35);(HERE/'staging-r1-validation.json').write_bytes(q.stdout);print(q.stdout.decode())
runtime=(HERE.parent/'kernel423/runtime.py').read_text().replace('stage=423','stage=424').replace('k423-tone-','k424-tone-')
runtime=runtime.replace("['r1','r2','r3']","['r1']");ast.parse(runtime);(HERE/'runtime.py').write_text(runtime)
