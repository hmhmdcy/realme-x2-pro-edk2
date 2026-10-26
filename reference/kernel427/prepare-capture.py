from pathlib import Path
import ast,hashlib,io,json,shlex,struct,sys,tarfile
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
run=sys.argv[1] if len(sys.argv)>1 else 'r1';assert run.startswith('r') and run[1:].isdigit() and 1<=int(run[1:])<=20
assert json.loads((P/'intree-build-state.json').read_text())['terminal']
build=json.loads((HERE/'intree-build-validation.json').read_text());assert build['passed'] and not build['diagnostics']
probe=json.loads((HERE/'capture-build-validation.json').read_text());assert probe['passed']
assert probe['source_sha256']==hashlib.sha256((HERE/'ds4-capture.c').read_bytes()).hexdigest()
assert probe['probe_sha256']==hashlib.sha256((P/'ds4-capture').read_bytes()).hexdigest()
prefix=(HERE.parent/'kernel342/native-install.py').read_text().split('def versions():')[0].replace("'stage':342","'stage':427")
source=prefix+'\n'+(HERE/'capture-worker-body.py').read_text();ast.parse(source);(P/'capture-worker.py').write_text(source)
files={'worker.py':P/'capture-worker.py','ds4-capture':P/'ds4-capture','params-private.bin':P/'params-private.bin','pipeline-fixture':P.parent/'kernel363/pipeline-fixture'}
proof={'modules':{}}
for row in build['modules']:
 if not row['runtime_candidate']:continue
 path=Path(row['private_path']);raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==row['sha256']
 shoff=struct.unpack_from('<Q',raw,40)[0];stride,count,strings=struct.unpack_from('<HHH',raw,58)
 sections=[struct.unpack_from('<IIQQQQIIQQ',raw,shoff+i*stride) for i in range(count)];ns=raw[sections[strings][4]:sections[strings][4]+sections[strings][5]]
 note=next(s for s in sections if ns[s[0]:].split(b'\0')[0]==b'.note.gnu.build-id');name=row['name'].replace('-','_');filename=row['name']+'.ko'
 files[filename]=path;proof['modules'][name]=dict(file=filename,sha256=row['sha256'],note_sha256=hashlib.sha256(raw[note[4]:note[4]+note[5]]).hexdigest())
(P/'capture-proof-private.json').write_text(json.dumps(proof,indent=2)+'\n');files['proof.json']=P/'capture-proof-private.json'
manifest={n:hashlib.sha256(p.read_bytes()).hexdigest() for n,p in files.items()};payload=io.BytesIO()
with tarfile.open(fileobj=payload,mode='w:gz') as tar:
 for n,p in files.items():tar.add(p,arcname=n)
 data=json.dumps(manifest).encode();member=tarfile.TarInfo('manifest.json');member.size=len(data);tar.addfile(member,io.BytesIO(data))
code='''from pathlib import Path
import hashlib,io,json,os,sys,tarfile
root=Path(ROOT);assert not root.exists()
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k394-recovered/boot-id-private.txt').read_bytes()
tar=tarfile.open(fileobj=io.BytesIO(sys.stdin.buffer.read()),mode='r:gz');members=tar.getmembers();assert {m.name for m in members}==NAMES and all(m.isfile() for m in members)
root.mkdir(mode=0o700)
for m in members:
 with (root/m.name).open('xb') as f:f.write(tar.extractfile(m).read());f.flush();os.fsync(f.fileno())
for n,digest in json.loads((root/'manifest.json').read_text()).items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==digest
for n in ['ds4-capture','pipeline-fixture']:(root/n).chmod(0o700)
print(json.dumps(dict(staged=True,root=str(root),passed=True)))
'''.replace('ROOT',repr('/var/lib/samurai/k427-ds4-'+run)).replace('NAMES',repr(set(files)|{'manifest.json'}))
q=host.ssh('python3 -c '+shlex.quote(code),input=payload.getvalue(),timeout=30);print(q.stdout.decode());q.check_returncode()
(HERE/('capture-staging-'+run+'-validation.json')).write_bytes(q.stdout)
