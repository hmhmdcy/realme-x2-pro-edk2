from pathlib import Path
import ast,hashlib,io,json,tarfile
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((HERE/'package-artifact-validation.json').read_text())['passed']
prefix=(HERE.parent/'kernel342/native-install.py').read_text().split('def versions():')[0].replace("'stage':342","'stage':391")
prefix=prefix.replace("marker.write_text(json.dumps(state,indent=2)+'\\n')", "tmp=root/'state.tmp';tmp.write_text(json.dumps(state,indent=2)+'\\n');tmp.replace(marker)")
source=prefix+'\n'+(HERE/'install-worker-body.py').read_text();ast.parse(source);worker=P/'install-worker.py';worker.write_text(source)
s=(HERE.parent/'kernel390/camera-client.py').read_text().replace("'stage':390","'stage':391").replace('stage=390','stage=391');needle=" env['LD_LIBRARY_PATH']=str(root/'lib')\n";assert s.count(needle)==1;s=s.replace(needle,'');ast.parse(s);(HERE/'camera-client.py').write_text(s)
collector=(HERE.parent/'kernel390/dump-collector.py').read_text().replace('start<300','start<600').replace('start>=300','start>=600');(HERE/'dump-collector.py').write_text(collector)
initial=json.loads((P/'initial-device-private.json').read_text());records=json.loads((P/'runtime-records.json').read_text())
proof=dict(stage=391,boot_guard='/var/lib/samurai/k390-active/boot-id-private.txt',old_packages=initial['packages'],packages={r['name']:r['version'] for r in records},private_defaults=initial['private_defaults'],installed_files=json.loads((P/'installed-file-sha256.json').read_text()),camss_note_sha256=hashlib.sha256((P.parent/'kernel390/qcom-camss.note').read_bytes()).hexdigest())
proofpath=P/'install-proof-private.json';proofpath.write_text(json.dumps(proof,indent=2)+'\n')
files={'worker.py':worker,'camera-client.py':HERE/'camera-client.py','dump-collector.py':HERE/'dump-collector.py','proof.json':proofpath}
for p in (P/'runtime-repository/forward').iterdir():files['repository/forward/'+p.name]=p
files['repository/rollback/packages.adb']=P/'runtime-repository/rollback/packages.adb'
cached={}
for p in (P/'runtime-repository/rollback').glob('*.apk'):cached['repository/rollback/'+p.name]=dict(path='/var/lib/samurai/k362-install-r1/repository/forward/'+p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
for n,remote,local in [('pipeline-fixture','/var/lib/samurai/k387-pipeline-r5/pipeline-fixture',P.parent/'kernel363/pipeline-fixture'),('pipeline-smoke','/var/lib/samurai/k387-pipeline-r5/pipeline-smoke',P.parent/'kernel388/pipeline-smoke')]:cached[n]=dict(path=remote,sha256=hashlib.sha256(local.read_bytes()).hexdigest())
# The ordinary PipeWire probe is retained from the previous installed package transaction.
cached['pw-hardware-probe']=dict(path='/var/lib/samurai/k362-install-r1/bin/pw-hardware-probe',sha256=hashlib.sha256((storage.SDK/'private/camss316-runtime/pw-hardware-probe').read_bytes()).hexdigest())
payload=P/'install-payload-private.tar.gz';assert not payload.exists()
with tarfile.open(payload,'w:gz') as tar:
 for n,p in files.items():tar.add(p,arcname=n,recursive=False)
metadata=dict(files_sha256={n:hashlib.sha256(p.read_bytes()).hexdigest() for n,p in files.items()},payload_sha256=hashlib.sha256(payload.read_bytes()).hexdigest(),cached=cached)
(P/'stage-manifest-private.json').write_text(json.dumps(metadata,indent=2)+'\n');print(json.dumps(dict(prepared=True,payload_bytes=payload.stat().st_size,forward_packages=7,rollback_packages_cached=7,installed=False)))
