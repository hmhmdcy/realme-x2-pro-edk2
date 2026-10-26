from pathlib import Path
import ast,hashlib,importlib.util,json,shlex,subprocess,tarfile
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
def record(name):
 d=json.loads((HERE/name).read_text());assert d['passed'] and not d.get('diagnostics');return d['modules'][0]
normal=record('intree-build-validation.json');test=record('test-intree-build-validation.json');assert json.loads((HERE/'stop-validation.json').read_text())['passed']
base=json.loads((P.parent/'kernel393/manifest-private.json').read_text());pair={r['module']:r for r in base['modules']};old=pair['qcom_camss_icp_a5_core'];adapter=pair['camss_icp_a5_m2m']
spec=importlib.util.spec_from_file_location('durable_prefix',HERE/'durable-prefix.py');prefix=importlib.util.module_from_spec(spec);spec.loader.exec_module(prefix)
worker=prefix.source()+'\n'+(HERE/'runtime-worker-body.py').read_text();ast.parse(worker);(P/'worker.py').write_text(worker)
collector=(HERE.parent/'kernel394/recovery-runtime-collected/dump-collector.py')
collector_source=(HERE.parent/'kernel391/dump-collector.py').read_text().replace('start<600','start<240').replace('start>=600','start>=240').replace('/var/lib/samurai/k390-active/boot-id-private.txt','/var/lib/samurai/k394-recovered/boot-id-private.txt');(P/'dump-collector.py').write_text(collector_source)
meta=dict(stage=395,release=base['release'],core_target=old['target'],old_core_sha256=old['new_sha256'],old_core_note_sha256=old['new_note_sha256'],new_core_sha256=normal['sha256'],other_files={adapter['target']:adapter['new_sha256']},unchanged_notes={'camss_icp_a5_m2m':adapter['new_note_sha256'],'qcom_camss':base['camss_note_sha256']},profiles=base['profiles'])
for kind,row in [('new',normal),('test',test)]:
 note=P/(kind+'-core.note');subprocess.run(['aarch64-linux-gnu-objcopy','-O','binary','--only-section=.note.gnu.build-id',row['private_path'],str(note)],check=True);meta[kind+'_core_note_sha256']=hashlib.sha256(note.read_bytes()).hexdigest()
assert not subprocess.check_output(['modinfo','-F','parm',normal['private_path']],text=True).strip()
assert 'test_drop_frame_ack' in subprocess.check_output(['modinfo','-F','parm',test['private_path']],text=True)
files={'worker.py':P/'worker.py','dump-collector.py':P/'dump-collector.py','ack-loss-client':P/'ack-loss-client','normal-core.ko':Path(normal['private_path']),'test-core.ko':Path(test['private_path'])}
meta['payload_sha256']={n:hashlib.sha256(p.read_bytes()).hexdigest() for n,p in files.items()};(P/'manifest-private.json').write_text(json.dumps(meta,indent=2)+'\n');files['manifest.json']=P/'manifest-private.json'
payload=P/'runtime-payload-private.tar.gz';assert not payload.exists()
with tarfile.open(payload,'w:gz') as t:
 for n,p in files.items():t.add(p,arcname=n,recursive=False)
root='/var/lib/samurai/k395-ack-loss-r1';code=r'''from pathlib import Path
import hashlib,json,os
root=Path(ROOT);assert not root.exists();meta=META;sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(meta['core_target'])==meta['old_core_sha256']
assert sha('/sys/module/qcom_camss_icp_a5_core/notes/.note.gnu.build-id')==meta['old_core_note_sha256']
s=json.loads(Path('/sys/bus/platform/devices/ac10000.icp/m2m_status').read_text());assert not any(s[k] for k in ['users','running','fatal','pinned','orphans'])
root.mkdir(mode=0o700);fd=os.open(root.parent,os.O_RDONLY|os.O_DIRECTORY)
try:os.fsync(fd)
finally:os.close(fd)
print(json.dumps(dict(staging_created=True,before=s)))
'''.replace('ROOT',repr(root)).replace('META',repr(meta))
q=host.ssh('python3 -c '+shlex.quote(code),timeout=25);(P/'preflight-private.json').write_bytes(q.stdout)
spec=importlib.util.spec_from_file_location('transport184',HERE.parent/'kernel184/host.py');transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport)
q=transport.upload(payload,root+'/payload-private.tar.gz');(P/'upload-private.log').write_bytes(q.stdout+q.stderr)
fixture_sha=hashlib.sha256((P.parent/'kernel363/pipeline-fixture').read_bytes()).hexdigest()
code=r'''from pathlib import Path
import hashlib,json,os,shutil,tarfile
root=Path(ROOT);assert hashlib.sha256((root/'payload-private.tar.gz').read_bytes()).hexdigest()==PAYLOAD_SHA
with tarfile.open(root/'payload-private.tar.gz','r:gz') as t:
 members=t.getmembers();assert {m.name for m in members}==NAMES and all(m.isfile() for m in members)
 for m in members:
  with (root/m.name).open('xb') as f:f.write(t.extractfile(m).read());f.flush();os.fsync(f.fileno())
with (root/'pipeline-fixture').open('xb') as f:f.write(Path('/var/lib/samurai/k391-install-r2/pipeline-fixture').read_bytes());f.flush();os.fsync(f.fileno())
assert hashlib.sha256((root/'pipeline-fixture').read_bytes()).hexdigest()==FIXTURE_SHA
for n in ['ack-loss-client','pipeline-fixture']:(root/n).chmod(0o700)
meta=json.loads((root/'manifest.json').read_text());meta['payload_sha256']['pipeline-fixture']=FIXTURE_SHA
with (root/'manifest.json').open('w') as f:f.write(json.dumps(meta)+'\n');f.flush();os.fsync(f.fileno())
for n,h in meta['payload_sha256'].items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==h
fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY)
try:os.fsync(fd)
finally:os.close(fd)
print(json.dumps(dict(stage=395,staged=True,normal_core_install_only_after_fault_recovery_verified=True,durable_files_and_directory=True,only_private_test_hook_until_then=True,passed=True)))
'''.replace('ROOT',repr(root)).replace('PAYLOAD_SHA',repr(hashlib.sha256(payload.read_bytes()).hexdigest())).replace('NAMES',repr(set(files))).replace('FIXTURE_SHA',repr(fixture_sha))
q=host.ssh('python3 -c '+shlex.quote(code),timeout=25);(HERE/'staging-validation.json').write_bytes(q.stdout);print(q.stdout.decode())
