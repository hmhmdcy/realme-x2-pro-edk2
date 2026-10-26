from pathlib import Path
import io,json,re,sys,tarfile
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;run=sys.argv[1] if len(sys.argv)>1 else 'r1';assert re.fullmatch(r'r\d+',run);root='/var/lib/samurai/k354-memory-'+run
build=json.loads((HERE/'intree-build-validation.json').read_text());assert build['passed'] and all(m['intree']=='Y' for m in build['modules'])
device=json.loads((P/'runtime-prerequisites-private.json').read_text());assert device['boot_matches']
manifest=dict(kernel_release=device['kernel_release'],phandle=device['phandle'])
payload=io.BytesIO()
with tarfile.open(fileobj=payload,mode='w:gz') as tar:
 for row in build['modules']:
  tar.add(row['private_path'],arcname='core.ko' if row['name']=='qcom-camss-icp-a5-core' else 'test.ko')
 tar.add(HERE/'memory-worker.py',arcname='worker.py')
 data=json.dumps(manifest).encode();info=tarfile.TarInfo('manifest.json');info.size=len(data);tar.addfile(info,io.BytesIO(data))
code="""from pathlib import Path;import io,tarfile,sys;root=Path('/var/lib/samurai/k354-memory-r1');assert not root.exists();assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k305-geometry-r2/boot-id-private.txt').read_bytes();raw=sys.stdin.buffer.read();tar=tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz');members=tar.getmembers();assert {m.name for m in members}=={'core.ko','test.ko','worker.py','manifest.json'} and all(m.isfile() for m in members);root.mkdir(mode=0o700);[(root.joinpath(m.name).write_bytes(tar.extractfile(m).read())) for m in members];print('Prepared temporary memory-only diagnostic.')"""
import shlex
code=code.replace('/var/lib/samurai/k354-memory-r1',root)
q=host.raw_ssh('python3 -c '+shlex.quote(code),input=payload.getvalue(),timeout=25);print(q.stdout.decode())
code="""from pathlib import Path;import subprocess,json;root=Path('/var/lib/samurai/k354-memory-r1');log=(root/'worker.log').open('xb');child=subprocess.Popen(['python3',str(root/'worker.py')],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);print(json.dumps(dict(pid=child.pid,root=str(root))))"""
code=code.replace('/var/lib/samurai/k354-memory-r1',root)
q=host.raw_ssh('python3 -c '+shlex.quote(code),timeout=15);(P/('launch-'+run+'-private.json')).write_bytes(q.stdout);print(q.stdout.decode())
