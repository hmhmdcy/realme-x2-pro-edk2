"""Stage a fresh bounded transaction with exact candidate modules and fallback."""
from pathlib import Path
import ast,hashlib,io,json,shlex,struct,sys,tarfile
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
storage.mount.mounted_build()
attempt=sys.argv[1] if len(sys.argv)>1 else 'r1'
assert attempt.startswith('r') and attempt[1:].isdigit() and 1<=int(attempt[1:])<=20
for name in ['preflight','runtime-inputs','client-build','geometry-contract','format-contract','native-bl','userspace-layout','reentry','aux-restart']:
 assert json.loads((HERE/(name+'-validation.json')).read_text())['passed'],name
baseline=json.loads((P/'preflight-private.json').read_text())
build=json.loads((HERE/'intree-build-validation.json').read_text());assert build['passed'] and not build['diagnostics']
userspace=json.loads((HERE/'build-validation.json').read_text());assert userspace['passed'] and userspace['private_ipa_version']==5
inputs=json.loads((P/'runtime-input-files-private.json').read_text())
guard=json.loads((P/'boot-adoption-private.json').read_text())['guard_path']
prefix=(HERE.parent/'kernel342/native-install.py').read_text().split('def versions():')[0].replace("'stage':342","'stage':441")
body=(HERE.parent/'kernel434/capture-worker-body.py').read_text()
a=body.index(" state['captures']={}");z=body.index('\nexcept BaseException:',a)
source=prefix+'\n'+body[:a]+(HERE/'auto-capture-body.py').read_text()+body[z:]
ast.parse(source);(P/'runtime-worker.py').write_text(source)
files={'worker.py':P/'runtime-worker.py','baseline-private.json':P/'preflight-private.json','pipeline-fixture':P.parent/'kernel363/pipeline-fixture','factory-s5kgw1-private.yaml':P.parent/'kernel440/factory-s5kgw1-private.yaml'}
if len(sys.argv)>2:
 assert sys.argv[2]=='diagnostic'
 (P/'diagnostic.json').write_text('{}\n');files['diagnostic.json']=P/'diagnostic.json'
for n in ['capture','pd10-ipe']:files[n]=P/n
for row in json.loads((HERE/'client-build-validation.json').read_text())['clients']:assert hashlib.sha256(files[row['name']].read_bytes()).hexdigest()==row['sha256']
for name,path in inputs.items():files[name]=Path(path['path']);assert hashlib.sha256(files[name].read_bytes()).hexdigest()==path['sha256']
proof=dict(modules={},boot_guard=guard)
for row in build['modules']:
 if not row['runtime_candidate']:continue
 path=Path(row['private_path']);raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==row['sha256']
 shoff=struct.unpack_from('<Q',raw,40)[0];stride,count,strings=struct.unpack_from('<HHH',raw,58)
 sections=[struct.unpack_from('<IIQQQQIIQQ',raw,shoff+i*stride) for i in range(count)]
 ns=raw[sections[strings][4]:sections[strings][4]+sections[strings][5]]
 note=next(s for s in sections if ns[s[0]:].split(b'\0')[0]==b'.note.gnu.build-id')
 filename=row['name']+'.ko';files[filename]=path
 proof['modules'][row['name'].replace('-','_')]=dict(file=filename,sha256=row['sha256'],note_sha256=hashlib.sha256(raw[note[4]:note[4]+note[5]]).hexdigest())
(P/'runtime-proof-private.json').write_text(json.dumps(proof,indent=2)+'\n');files['proof.json']=P/'runtime-proof-private.json'
manifest={n:hashlib.sha256(p.read_bytes()).hexdigest() for n,p in files.items()};payload=io.BytesIO()
with tarfile.open(fileobj=payload,mode='w:gz') as tar:
 for n,p in files.items():tar.add(p,arcname=n)
 data=json.dumps(manifest).encode();m=tarfile.TarInfo('manifest.json');m.size=len(data);tar.addfile(m,io.BytesIO(data))
code='''from pathlib import Path
import hashlib,io,json,os,sys,tarfile
root=Path(ROOT);assert not root.exists()
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path(GUARD).read_bytes()
tar=tarfile.open(fileobj=io.BytesIO(sys.stdin.buffer.read()),mode='r:gz');members=tar.getmembers()
assert {m.name for m in members}==NAMES and all(m.isfile() for m in members)
root.mkdir(mode=0o700)
for m in members:
 p=root/m.name;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(tar.extractfile(m).read());f.flush();os.fsync(f.fileno())
for n,h in json.loads((root/'manifest.json').read_text()).items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==h
for n in ['capture','pd10-ipe','pipeline-fixture','proxy/camss_ipa_proxy']:(root/n).chmod(0o700)
for n in ['libcamera','libcamera-base']:(root/f'lib/{n}.so.0.7').symlink_to(f'{n}.so.0.7.2')
print(json.dumps(dict(stage=441,staged=True,root=str(root),passed=True)))
'''.replace('ROOT',repr('/var/lib/samurai/k441-variable-pd10-'+attempt)).replace('GUARD',repr(guard)).replace('NAMES',repr(set(files)|{'manifest.json'}))
q=host.ssh('python3 -c '+shlex.quote(code),input=payload.getvalue(),timeout=60);q.check_returncode()
(HERE/('runtime-staging-'+attempt+'-validation.json')).write_bytes(q.stdout);print(q.stdout.decode())
