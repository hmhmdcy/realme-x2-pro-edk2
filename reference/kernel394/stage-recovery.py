from pathlib import Path
import ast,base64,hashlib,json,shlex
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;assert json.loads((HERE/'postboot-validation.json').read_text())['passed']
prefix=(HERE.parent/'kernel342/native-install.py').read_text().split('def versions():')[0].replace("'stage':342","'stage':394");prefix=prefix.replace("marker.write_text(json.dumps(state,indent=2)+'\\n')", "tmp=root/'state.tmp';tmp.write_text(json.dumps(state,indent=2)+'\\n');tmp.replace(marker)")
worker=prefix+'\n'+(HERE/'recovery-worker-body.py').read_text();ast.parse(worker)
collector=(HERE.parent/'kernel391/dump-collector.py').read_text().replace('start<600','start<240').replace('start>=600','start>=240').replace('/var/lib/samurai/k390-active/boot-id-private.txt','/var/lib/samurai/k394-recovered/boot-id-private.txt')
meta=json.loads((P/'manifest-private.json').read_text());meta['payload_sha256']={'worker.py':hashlib.sha256(worker.encode()).hexdigest(),'dump-collector.py':hashlib.sha256(collector.encode()).hexdigest(),'pipeline-fixture':hashlib.sha256((P.parent/'kernel363/pipeline-fixture').read_bytes()).hexdigest()}
code=r'''from pathlib import Path
import base64,hashlib,json,shutil
root=Path('/var/lib/samurai/k394-camera-recovery-r1');assert not root.exists();root.mkdir(mode=0o700);meta=META
(root/'worker.py').write_bytes(base64.b64decode(WORKER));(root/'dump-collector.py').write_bytes(base64.b64decode(COLLECTOR));shutil.copyfile('/var/lib/samurai/k391-install-r2/pipeline-fixture',root/'pipeline-fixture');(root/'pipeline-fixture').chmod(0o700)
for n,h in meta['payload_sha256'].items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==h
(root/'manifest.json').write_text(json.dumps(meta)+'\n');print(json.dumps(dict(stage=394,recovered_boot_normal_four_camera_staged=True,no_new_fault_injection=True,passed=True)))
'''.replace('META',repr(meta)).replace('WORKER',repr(base64.b64encode(worker.encode()).decode())).replace('COLLECTOR',repr(base64.b64encode(collector.encode()).decode()))
q=host.ssh('python3 -c '+shlex.quote(code),timeout=25);(HERE/'recovery-staging-validation.json').write_bytes(q.stdout);print(q.stdout.decode())
