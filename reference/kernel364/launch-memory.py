"""Check actual IOMMU mapping/unload on k363 before starting an A5 CPU."""
from pathlib import Path
import io,json,re,shlex,sys,tarfile
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;name=sys.argv[1];assert re.fullmatch(r'r[1-9][0-9]*',name)
build=json.loads((HERE/'intree-build-validation.json').read_text());assert build['passed']
rows={r['name']:r for r in build['modules']};adopted=json.loads((P.parent/'kernel363/postboot-adoption-private.json').read_text())
manifest=dict(kernel_release=rows['qcom-camss-icp-a5-core']['vermagic'].split()[0],phandle=build['firmware_region']['smmu'],boot_guard=adopted['guard_path'])
payload=io.BytesIO()
with tarfile.open(fileobj=payload,mode='w:gz') as tar:
 for key,file in [('core.ko',Path(rows['qcom-camss-icp-a5-core']['private_path'])),('test.ko',Path(rows['camss-icp-a5-memory-test']['private_path'])),('worker.py',HERE/'memory-worker.py')]:tar.add(file,arcname=key)
 raw=json.dumps(manifest).encode();entry=tarfile.TarInfo('manifest.json');entry.size=len(raw);tar.addfile(entry,io.BytesIO(raw))
code=r'''
from pathlib import Path
import io,sys,json,subprocess,tarfile
root=Path(ROOT)
if root.exists():print(json.dumps(dict(existing=True,state=json.loads((root/'state.json').read_text()) if (root/'state.json').exists() else None)));raise SystemExit(0)
root.mkdir(mode=0o700)
with tarfile.open(fileobj=io.BytesIO(sys.stdin.buffer.read()),mode='r:gz') as tar:
 members=tar.getmembers();assert {m.name for m in members}=={'core.ko','test.ko','worker.py','manifest.json'} and all(m.isfile() for m in members);tar.extractall(root,filter='data')
with (root/'worker.log').open('xb') as log:
 child=subprocess.Popen(['python3',str(root/'worker.py')],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
print(json.dumps(dict(pid=child.pid,root=str(root))))
'''.replace('ROOT',repr('/var/lib/samurai/k364-memory-'+name))
q=host.ssh('python3 -c '+shlex.quote(code),input=payload.getvalue(),timeout=30);(P/('memory-launch-'+name+'-private.json')).write_bytes(q.stdout);print(q.stdout.decode())
