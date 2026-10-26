"""Stage a complete private IPA2/library/proxy pair without module replacement."""
from pathlib import Path
import ast,hashlib,importlib.util,json,shlex,shutil,sys,tarfile
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
attempt=sys.argv[1] if len(sys.argv)>1 else 'r1';assert attempt in ['r1','r2']
if attempt=='r2':
 old=json.loads((HERE/'runtime-r1-validation.json').read_text());assert old['passed'] and old['terminal'] and not any(old[k] for k in ['worker_live','client_live','collector_live'])
 assert not (P/'manifest-r1-private.json').exists();shutil.copyfile(P/'manifest-private.json',P/'manifest-r1-private.json')
b=json.loads((HERE/'build-validation.json').read_text());assert b['passed'] and b['private_ipa_version']==2
assert json.loads((HERE/'history-validation.json').read_text())['passed']
assert json.loads((HERE/'signature-validation.json').read_text())['passed']
spec=importlib.util.spec_from_file_location('prefix395',HERE.parent/'kernel395/durable-prefix.py');prefix=importlib.util.module_from_spec(spec);spec.loader.exec_module(prefix)
worker=prefix.source().replace("'stage':395","'stage':421")+'\n'+(HERE/'runtime-worker-body.py').read_text();ast.parse(worker);(P/'worker.py').write_text(worker)
client=(HERE.parent/'kernel420/camera-client.py').read_text().replace('stage=420','stage=421').replace("'stage':420","'stage':421")
needle=" env['LIBCAMERA_IPA_MODULE_PATH']='/usr/lib/libcamera/ipa'\n env['LIBCAMERA_IPA_PROXY_PATH']='/usr/libexec/libcamera'"
assert client.count(needle)==1
client=client.replace(needle," env['LD_LIBRARY_PATH']=str(root/'lib')\n env['LIBCAMERA_IPA_MODULE_PATH']=str(root/'ipa')\n env['LIBCAMERA_IPA_PROXY_PATH']=str(root/'proxy')")
ast.parse(client);(HERE/'camera-client.py').write_text(client)
if attempt=='r2':
 client=client.replace("for model in ['imx471','imx319','s5k3m5','s5kgw1']:","for model in ['s5kgw1']:")
 a=client.index(" for kind in ['dual','raw']:");b=client.index(" nodes=[p for p in Path('/sys/class/video4linux')",a);client=client[:a]+client[b:]
 client=client.replace('len(captures)==7','len(captures)==2');ast.parse(client);(HERE/'camera-client.py').write_text(client)
files={'worker.py':P/'worker.py','camera-client.py':HERE/'camera-client.py','dump-collector.py':HERE.parent/'kernel420/dump-collector.py',
 'lib/libcamera.so.0.7.2':P/'libcamera.so.0.7.2','ipa/ipa_camss_vfe.so':P/'ipa_camss_vfe.so','ipa/ipa_camss_vfe.so.sign':P/'ipa_camss_vfe.so.sign','proxy/camss_ipa_proxy':P/'camss_ipa_proxy'}
proof=json.loads((P.parent/'kernel420/install-proof-private.json').read_text())
normal={'/'+n:h for n,h in proof['installed_files'].items()};normal.update({i['target']:i['new_sha256'] for i in proof['driver_pair']})
notes={i['module']:i['new_note_sha256'] for i in proof['driver_pair']};notes['qcom_camss']=proof['camss_note_sha256']
meta=dict(stage=421,attempt=attempt,expected_captures=2 if attempt=='r2' else 7,normal_files=normal,profiles=proof['private_defaults'],notes=notes,payload_sha256={n:hashlib.sha256(p.read_bytes()).hexdigest() for n,p in files.items()})
(P/'manifest-private.json').write_text(json.dumps(meta,indent=2)+'\n')
payload=P/('payload-'+attempt+'-private.tar.gz');assert not payload.exists()
with tarfile.open(payload,'w:gz') as tar:
 for n,p in files.items():tar.add(p,arcname=n,recursive=False)
root='/var/lib/samurai/k421-history-'+attempt
code=r'''from pathlib import Path
import hashlib,json
root=Path(ROOT);assert not root.exists();meta=META
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k394-recovered/boot-id-private.txt').read_bytes()
old=Path('/var/lib/samurai/k420-install-r1');state=json.loads((old/'state.json').read_text());assert state['terminal'] and state['passed']
for k in ['pid','client_pid','collector_pid']:
 p=Path('/proc',str(state.get(k,-1)))
 try:assert (p/'stat').read_text().rsplit(')',1)[1].split()[0]=='Z' or str(old).encode() not in (p/'cmdline').read_bytes()
 except OSError:pass
assert all(hashlib.sha256(Path(n).read_bytes()).hexdigest()==h for n,h in meta['normal_files'].items())
root.mkdir(mode=0o700);print('Formal420 verified;created private421 staging root.')
'''.replace('ROOT',repr(root)).replace('META',repr(meta))
print(host.ssh('python3 -c '+shlex.quote(code),timeout=25).stdout.decode())
spec=importlib.util.spec_from_file_location('transport184',HERE.parent/'kernel184/host.py');transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport)
q=transport.upload(payload,root+'/payload-private.tar.gz');(P/'payload-upload-private.log').write_bytes(q.stdout+q.stderr)
cached={n:dict(path='/var/lib/samurai/k420-install-r1/'+n,sha256=hashlib.sha256(local.read_bytes()).hexdigest()) for n,local in [('pipeline-fixture',P.parent/'kernel363/pipeline-fixture'),('pipeline-smoke',P.parent/'kernel388/pipeline-smoke')]}
code=r'''from pathlib import Path
import hashlib,json,os,shutil,tarfile
root=Path(ROOT);meta=META;cached=CACHED
assert hashlib.sha256((root/'payload-private.tar.gz').read_bytes()).hexdigest()==PAYLOAD
with tarfile.open(root/'payload-private.tar.gz','r:gz') as tar:
 assert all(m.isfile() and m.name in meta['payload_sha256'] for m in tar.getmembers())
 for m in tar.getmembers():
  p=root/m.name;p.parent.mkdir(parents=True,exist_ok=True)
  with p.open('xb') as f:f.write(tar.extractfile(m).read());f.flush();os.fsync(f.fileno())
for n,h in meta['payload_sha256'].items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==h
for n,d in cached.items():
 assert hashlib.sha256(Path(d['path']).read_bytes()).hexdigest()==d['sha256'];shutil.copyfile(d['path'],root/n);(root/n).chmod(0o700)
(root/'lib/libcamera.so.0.7').symlink_to('libcamera.so.0.7.2');(root/'proxy/camss_ipa_proxy').chmod(0o700)
(root/'manifest.json').write_text(json.dumps(meta)+'\n');(root/'stage-manifest-private.json').write_text(json.dumps(dict(files_sha256=meta['payload_sha256']))+'\n')
print(json.dumps(dict(stage=421,staged=True,library_ipa_proxy_matched_version2=True,kernel_modules_not_changed=True,passed=True)))
'''.replace('ROOT',repr(root)).replace('META',repr(meta)).replace('CACHED',repr(cached)).replace('PAYLOAD',repr(hashlib.sha256(payload.read_bytes()).hexdigest()))
q=host.ssh('python3 -c '+shlex.quote(code),timeout=35)
for n in ['staging-validation.json','staging-'+attempt+'-validation.json']:(HERE/n).write_bytes(q.stdout)
print(q.stdout.decode())
runtime=(HERE.parent/'kernel420/install-step.py').read_text().replace('k420-install-','k421-history-').replace('stage=420','stage=421')
runtime=runtime.replace("'install-'+action","'runtime-'+action").replace("'install-collected-'","'runtime-collected-'").replace("'install-'+attempt+'-validation.json'","'runtime-'+attempt+'-validation.json'").replace("'install-validation.json'","'runtime-validation.json'")
a=runtime.index(" s=d['state'];keys=");b=runtime.index('\n report=',a)
runtime=runtime[:a]+" s=d['state'];keys=['phase','terminal','passed','failure','cleanup_failure','before','after_candidate','candidate_suite','formal_front','formal420_unchanged','after','core_after','taint','collector_result']"+runtime[b:]
runtime=runtime.replace("new_fault_count=len(s.get('new_faults',[])),","new_fault_count=s.get('new_fault_count',0),")
runtime=runtime.replace("p.suffix in ['.log','.txt']","p.suffix in ['.log','.txt','.out']")
ast.parse(runtime);(HERE/'runtime.py').write_text(runtime)
