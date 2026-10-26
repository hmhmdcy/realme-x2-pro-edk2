from pathlib import Path
import ast,hashlib,importlib.util,json,shlex,subprocess,tarfile
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
normal=json.loads((HERE/'intree-build-validation.json').read_text());test=json.loads((HERE/'test-intree-build-validation.json').read_text());assert normal['passed'] and test['passed'] and not normal['diagnostics'] and not test['diagnostics']
core=normal['modules'][0];adapter=next(r for r in test['modules'] if r['name']=='camss-icp-a5-m2m') # current fixed LTM adapter; normal job ABI remains unchanged
assert 'test_ltm_mode' in subprocess.check_output(['modinfo','-F','parm',adapter['private_path']],text=True)
assert not subprocess.check_output(['modinfo','-F','parm',core['private_path']],text=True).strip()
spec=importlib.util.spec_from_file_location('prefix395',HERE.parent/'kernel395/durable-prefix.py');prefix=importlib.util.module_from_spec(spec);spec.loader.exec_module(prefix)
worker=prefix.source().replace("'stage':395","'stage':406")+'\n'+(HERE/'runtime-worker-body.py').read_text();ast.parse(worker);(P/'worker.py').write_text(worker)
collector=(HERE.parent/'kernel391/dump-collector.py').read_text().replace('start<600','start<360').replace('start>=600','start>=360').replace('/var/lib/samurai/k390-active/boot-id-private.txt','/var/lib/samurai/k394-recovered/boot-id-private.txt');(P/'dump-collector.py').write_text(collector)
old=json.loads((P.parent/'kernel395/manifest-private.json').read_text())
meta=dict(stage=406,normal_files={old['core_target']:old['new_core_sha256'],**old['other_files']},profiles=old['profiles'],normal_core_note_sha256=old['new_core_note_sha256'],normal_adapter_note_sha256=old['unchanged_notes']['camss_icp_a5_m2m'],camss_note_sha256=old['unchanged_notes']['qcom_camss'])
for kind,row in [('candidate_core',core),('candidate_adapter',adapter)]:
 note=P/(kind+'.note');subprocess.run(['aarch64-linux-gnu-objcopy','-O','binary','--only-section=.note.gnu.build-id',row['private_path'],str(note)],check=True);meta[kind+'_note_sha256']=hashlib.sha256(note.read_bytes()).hexdigest()
files={'candidate-core.ko':Path(core['private_path']),'test-adapter.ko':Path(adapter['private_path']),'colour-client':P/'colour-client','worker.py':P/'worker.py','dump-collector.py':P/'dump-collector.py'}
meta['payload_sha256']={n:hashlib.sha256(p.read_bytes()).hexdigest() for n,p in files.items()};(P/'manifest-private.json').write_text(json.dumps(meta,indent=2)+'\n');files['manifest.json']=P/'manifest-private.json'
payload=P/'payload-r2-private.tar.gz';assert not payload.exists()
with tarfile.open(payload,'w:gz') as tar:
 for n,p in files.items():tar.add(p,arcname=n,recursive=False)
root='/var/lib/samurai/k406-ltm-r2';code=r'''from pathlib import Path
import hashlib,json,os
root=Path(ROOT);assert not root.exists();meta=META;sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert all(sha(n)==h for n,h in meta['normal_files'].items())
assert sha('/sys/module/qcom_camss_icp_a5_core/notes/.note.gnu.build-id')==meta['normal_core_note_sha256']
assert sha('/sys/module/camss_icp_a5_m2m/notes/.note.gnu.build-id')==meta['normal_adapter_note_sha256']
root.mkdir(mode=0o700);print(json.dumps(dict(created=True,before=json.loads(Path('/sys/bus/platform/devices/ac10000.icp/m2m_status').read_text()))))
'''.replace('ROOT',repr(root)).replace('META',repr(meta))
q=host.ssh('python3 -c '+shlex.quote(code),timeout=25);(P/'preflight-private.json').write_bytes(q.stdout)
spec=importlib.util.spec_from_file_location('transport184',HERE.parent/'kernel184/host.py');transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport)
q=transport.upload(payload,root+'/payload-private.tar.gz');(P/'upload-private.log').write_bytes(q.stdout+q.stderr)
fixture_sha=hashlib.sha256((P.parent/'kernel363/pipeline-fixture').read_bytes()).hexdigest()
code=r'''from pathlib import Path
import hashlib,json,os,tarfile
root=Path(ROOT);sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();assert sha(root/'payload-private.tar.gz')==PAYLOAD
with tarfile.open(root/'payload-private.tar.gz','r:gz') as tar:
 members=tar.getmembers();assert {m.name for m in members}==NAMES and all(m.isfile() for m in members)
 for m in members:
  with (root/m.name).open('xb') as f:f.write(tar.extractfile(m).read());f.flush();os.fsync(f.fileno())
with (root/'pipeline-fixture').open('xb') as f:f.write(Path('/var/lib/samurai/k391-install-r2/pipeline-fixture').read_bytes());f.flush();os.fsync(f.fileno())
assert sha(root/'pipeline-fixture')==FIXTURE
meta=json.loads((root/'manifest.json').read_text());meta['payload_sha256']['pipeline-fixture']=FIXTURE
with (root/'manifest.json').open('w') as f:f.write(json.dumps(meta));f.flush();os.fsync(f.fileno())
for n,h in meta['payload_sha256'].items():assert sha(root/n)==h
for n in ['pipeline-fixture','colour-client']:(root/n).chmod(0o700)
for p in [root,root.parent]:
 fd=os.open(p,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)
print(json.dumps(dict(stage=406,staged=True,normal_module_files_not_replaced=True,test_adapter_only_loaded_privately=True,durable_staging=True,passed=True)))
'''.replace('ROOT',repr(root)).replace('PAYLOAD',repr(hashlib.sha256(payload.read_bytes()).hexdigest())).replace('NAMES',repr(set(files))).replace('FIXTURE',repr(fixture_sha))
q=host.ssh('python3 -c '+shlex.quote(code),timeout=25);(HERE/'staging-validation-r2.json').write_bytes(q.stdout)
print(q.stdout.decode())
