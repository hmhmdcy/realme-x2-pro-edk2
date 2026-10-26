"""Stage verified IPA5 against the already-tested matched kernel434 modules."""
from pathlib import Path
import ast,hashlib,io,json,shlex,struct,sys,tarfile
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
attempt=sys.argv[1] if len(sys.argv)>1 else 'r1';assert attempt.startswith('r') and attempt[1:].isdigit()
for name in ['ipa','history','native-gtm','profile-export','preflight','source','retention']:assert json.loads((HERE/(name+'-validation.json')).read_text())['passed']
build=json.loads((HERE.parent/'kernel434/intree-build-validation.json').read_text());assert build['passed'] and build['attempt']==1 and not build['diagnostics']
userspace=json.loads((HERE/'build-validation.json').read_text());assert userspace['passed'] and userspace['private_ipa_version']==5
assert json.loads((HERE/'ipa-validation.json').read_text())['actual_ipa_sha256']==hashlib.sha256((P/'ipa_camss_vfe.so').read_bytes()).hexdigest()
baseline=json.loads((P/'preflight-stdout-private.json').read_text());guard=json.loads((P.parent/'kernel429/postboot-adoption-private.json').read_text())['guard_path']
prefix=(HERE.parent/'kernel342/native-install.py').read_text().split('def versions():')[0].replace("'stage':342","'stage':435")
body=(HERE.parent/'kernel434/capture-worker-body.py').read_text();a=body.index(" state['captures']={}");z=body.index('\nexcept BaseException:',a)
body=body[:a]+(HERE/'auto-capture-body.py').read_text()+body[z:]
source=prefix+'\n'+body;ast.parse(source);(P/'runtime-worker.py').write_text(source)
files={'worker.py':P/'runtime-worker.py','capture':P.parent/'kernel423/capture','pipeline-fixture':P.parent/'kernel363/pipeline-fixture','factory-s5kgw1-private.yaml':P/'factory-s5kgw1-private.yaml','baseline-private.json':P/'preflight-stdout-private.json'}
for n in ['libcamera.so.0.7.2','ipa_camss_vfe.so','ipa_camss_vfe.so.sign','camss_ipa_proxy']:
 path=P/n;row=next(r for r in userspace['runtime_files'] if r['name']==n);assert hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256'];files[('lib/' if n.startswith('libcamera') else 'proxy/' if n=='camss_ipa_proxy' else 'ipa/')+n]=path
proof=dict(modules={},boot_guard=guard)
for row in build['modules']:
 if not row['runtime_candidate']:continue
 path=Path(row['private_path']);raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==row['sha256']
 shoff=struct.unpack_from('<Q',raw,40)[0];stride,count,strings=struct.unpack_from('<HHH',raw,58);sections=[struct.unpack_from('<IIQQQQIIQQ',raw,shoff+i*stride) for i in range(count)];ns=raw[sections[strings][4]:sections[strings][4]+sections[strings][5]]
 note=next(s for s in sections if ns[s[0]:].split(b'\0')[0]==b'.note.gnu.build-id');name=row['name'].replace('-','_');filename=row['name']+'.ko';files[filename]=path;proof['modules'][name]=dict(file=filename,sha256=row['sha256'],note_sha256=hashlib.sha256(raw[note[4]:note[4]+note[5]]).hexdigest())
(P/'runtime-proof-private.json').write_text(json.dumps(proof,indent=2)+'\n');files['proof.json']=P/'runtime-proof-private.json'
manifest={n:hashlib.sha256(p.read_bytes()).hexdigest() for n,p in files.items()};payload=io.BytesIO()
with tarfile.open(fileobj=payload,mode='w:gz') as tar:
 for n,p in files.items():tar.add(p,arcname=n)
 data=json.dumps(manifest).encode();member=tarfile.TarInfo('manifest.json');member.size=len(data);tar.addfile(member,io.BytesIO(data))
code='''from pathlib import Path
import hashlib,io,json,os,sys,tarfile
root=Path(ROOT);assert not root.exists()
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path(GUARD).read_bytes()
tar=tarfile.open(fileobj=io.BytesIO(sys.stdin.buffer.read()),mode='r:gz');members=tar.getmembers();assert {m.name for m in members}==NAMES and all(m.isfile() for m in members)
root.mkdir(mode=0o700)
for m in members:
 p=root/m.name;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(tar.extractfile(m).read());f.flush();os.fsync(f.fileno())
for n,digest in json.loads((root/'manifest.json').read_text()).items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==digest
for n in ['capture','pipeline-fixture','proxy/camss_ipa_proxy']:(root/n).chmod(0o700)
(root/'lib/libcamera.so.0.7').symlink_to('libcamera.so.0.7.2')
print(json.dumps(dict(staged=True,root=str(root),passed=True)))
'''.replace('ROOT',repr('/var/lib/samurai/k435-gtm-auto-'+attempt)).replace('GUARD',repr(guard)).replace('NAMES',repr(set(files)|{'manifest.json'}))
q=host.ssh('python3 -c '+shlex.quote(code),input=payload.getvalue(),timeout=45);q.check_returncode();(HERE/('runtime-staging-'+attempt+'-validation.json')).write_bytes(q.stdout);print(q.stdout.decode())
