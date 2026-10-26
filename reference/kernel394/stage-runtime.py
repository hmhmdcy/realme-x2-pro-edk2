from pathlib import Path
import ast,hashlib,importlib.util,json,shlex,subprocess,tarfile
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
build=json.loads((HERE/'intree-build-validation.json').read_text());assert build['passed'] and not build['diagnostics'];test=Path(build['modules'][0]['private_path'])
assert json.loads((HERE/'client-build-validation.json').read_text())['passed']
base=json.loads((P.parent/'kernel393/manifest-private.json').read_text());pair={r['module']:r for r in base['modules']}
note=P/'test-core.note';subprocess.run(['aarch64-linux-gnu-objcopy','-O','binary','--only-section=.note.gnu.build-id',str(test),str(note)],check=True)
prefix=(HERE.parent/'kernel342/native-install.py').read_text().split('def versions():')[0].replace("'stage':342","'stage':394")
prefix=prefix.replace("marker.write_text(json.dumps(state,indent=2)+'\\n')", "tmp=root/'state.tmp';tmp.write_text(json.dumps(state,indent=2)+'\\n');tmp.replace(marker)")
worker=prefix+'\n'+(HERE/'runtime-worker-body.py').read_text();ast.parse(worker);(P/'worker.py').write_text(worker)
collector=(HERE.parent/'kernel391/dump-collector.py').read_text().replace('start<600','start<240').replace('start>=600','start>=240');(P/'dump-collector.py').write_text(collector)
files={'worker.py':P/'worker.py','dump-collector.py':P/'dump-collector.py','ack-loss-client':P/'ack-loss-client','test-core.ko':test}
meta=dict(stage=394,payload_sha256={n:hashlib.sha256(p.read_bytes()).hexdigest() for n,p in files.items()},normal_files={r['target']:r['new_sha256'] for r in base['modules']},profiles=base['profiles'],normal_core_note_sha256=pair['qcom_camss_icp_a5_core']['new_note_sha256'],test_core_note_sha256=hashlib.sha256(note.read_bytes()).hexdigest(),unchanged_notes={'camss_icp_a5_m2m':pair['camss_icp_a5_m2m']['new_note_sha256'],'qcom_camss':base['camss_note_sha256']})
(P/'manifest-private.json').write_text(json.dumps(meta,indent=2)+'\n');files['manifest.json']=P/'manifest-private.json'
payload=P/'runtime-payload-private.tar.gz';assert not payload.exists()
with tarfile.open(payload,'w:gz') as t:
 for n,p in files.items():t.add(p,arcname=n,recursive=False)
root='/var/lib/samurai/k394-ack-loss-r1';code=r'''from pathlib import Path
import hashlib,json
root=Path(ROOT);assert not root.exists();meta=META
assert all(hashlib.sha256(Path(n).read_bytes()).hexdigest()==h for n,h in meta['normal_files'].items())
dev=Path('/sys/bus/platform/devices/ac10000.icp');s=json.loads((dev/'m2m_status').read_text());assert not any(s[n] for n in ['users','running','fatal','pinned','orphans'])
assert not Path('/sys/module/qcom_camss_icp_a5_core/parameters/test_drop_frame_ack').exists()
root.mkdir(mode=0o700);print(json.dumps(dict(before=s,created=True)))
'''.replace('ROOT',repr(root)).replace('META',repr(meta))
q=host.ssh('python3 -c '+shlex.quote(code),timeout=25);(P/'preflight-private.json').write_bytes(q.stdout)
spec=importlib.util.spec_from_file_location('transport184',HERE.parent/'kernel184/host.py');transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport)
q=transport.upload(payload,root+'/payload-private.tar.gz');(P/'upload-private.log').write_bytes(q.stdout+q.stderr)
fixture_sha=hashlib.sha256((P.parent/'kernel363/pipeline-fixture').read_bytes()).hexdigest()
code=r'''from pathlib import Path
import hashlib,json,shutil,tarfile
root=Path(ROOT);assert hashlib.sha256((root/'payload-private.tar.gz').read_bytes()).hexdigest()==PAYLOAD_SHA
with tarfile.open(root/'payload-private.tar.gz','r:gz') as t:
 members=t.getmembers();assert {m.name for m in members}==NAMES and all(m.isfile() for m in members)
 for m in members:
  with (root/m.name).open('xb') as f:f.write(t.extractfile(m).read())
shutil.copyfile('/var/lib/samurai/k391-install-r2/pipeline-fixture',root/'pipeline-fixture');assert hashlib.sha256((root/'pipeline-fixture').read_bytes()).hexdigest()==FIXTURE_SHA
for n in ['ack-loss-client','pipeline-fixture']:(root/n).chmod(0o700)
meta=json.loads((root/'manifest.json').read_text());meta['payload_sha256']['pipeline-fixture']=FIXTURE_SHA;(root/'manifest.json').write_text(json.dumps(meta)+'\n')
for n,h in meta['payload_sha256'].items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==h
print(json.dumps(dict(stage=394,staged=True,normal_module_files_not_replaced=True,temporary_core_only_from_private_stage=True,passed=True)))
'''.replace('ROOT',repr(root)).replace('PAYLOAD_SHA',repr(hashlib.sha256(payload.read_bytes()).hexdigest())).replace('NAMES',repr(set(files))).replace('FIXTURE_SHA',repr(fixture_sha))
q=host.ssh('python3 -c '+shlex.quote(code),timeout=25);(HERE/'staging-validation.json').write_bytes(q.stdout);print(q.stdout.decode())
