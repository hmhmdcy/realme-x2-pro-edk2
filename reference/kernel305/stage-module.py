from pathlib import Path
import hashlib,io,json,shlex,struct,tarfile
import host
HERE=Path(__file__).resolve().parent
build=json.loads((HERE/'kernel-build-validation.json').read_text())
proof=json.loads((HERE/'services-preflight-validation.json').read_text())
tool=json.loads((HERE/'geometry-probe-tool-validation.json').read_text())
assert build['exit_code']==0 and not build['diagnostics']
module=host.PRIVATE/'s5k3m5-geometry305-private.ko'
binary=host.PRIVATE/'sensor-geometry-aarch64-private'
assert hashlib.sha256(module.read_bytes()).hexdigest()==build['module_sha256']
assert hashlib.sha256(binary.read_bytes()).hexdigest()==tool['binary_sha256']
def note(raw):
 offset=struct.unpack_from('<Q',raw,40)[0];size,count,strings=struct.unpack_from('<HHH',raw,58)
 sections=[struct.unpack_from('<IIQQQQIIQQ',raw,offset+i*size) for i in range(count)]
 names=raw[sections[strings][4]:sections[strings][4]+sections[strings][5]]
 return next(raw[x[4]:x[4]+x[5]] for x in sections if names[x[0]:].split(b'\0',1)[0]==b'.note.gnu.build-id')
q=host.ssh("cat /usr/lib/modules/7.3.0-rc6-rmx1931-samurai-k298+/kernel/drivers/media/i2c/s5k3m5.ko",timeout=20)
assert hashlib.sha256(q.stdout).hexdigest()==proof['original_sha256']
assert hashlib.sha256(note(q.stdout)).hexdigest()==proof['loaded_note_sha256']
original=host.PRIVATE/'s5k3m5-original-phone-private.ko'
assert not original.exists();original.write_bytes(q.stdout)
files={'s5k3m5.ko':module,'sensor-geometry':binary}
archive=host.PRIVATE/'sensor-candidate-private.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
 for name,path in files.items():
  data=path.read_bytes();entry=tarfile.TarInfo(name);entry.size=len(data);entry.mode=0o700 if name=='sensor-geometry' else 0o600
  tar.addfile(entry,io.BytesIO(data))
manifest={n:dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for n,p in files.items()}
code=r'''
from pathlib import Path
import hashlib,io,json,sys,tarfile
root=Path('/var/lib/samurai/k305-sensor-candidate')
assert (root/'preflight-private.json').is_file() and not (root/'payload').exists()
data=sys.stdin.buffer.read();assert hashlib.sha256(data).hexdigest()==ARCHIVE
expected=EXPECTED
with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as tar:
 assert set(tar.getnames())==set(expected)
 for member in tar.getmembers():
  assert member.isfile() and '..' not in Path(member.name).parts and not member.name.startswith('/')
  b=tar.extractfile(member).read();assert len(b)==expected[member.name]['bytes'] and hashlib.sha256(b).hexdigest()==expected[member.name]['sha256']
 target=root/'payload';target.mkdir(mode=0o700);tar.extractall(target,filter='data')
(root/'payload-manifest-private.json').write_text(json.dumps(expected,indent=2)+'\n')
print('CANDIDATE_STAGED_NO_DEVICE_CHANGE')
'''.replace('ARCHIVE',repr(hashlib.sha256(archive.read_bytes()).hexdigest())).replace('EXPECTED',repr(manifest))
q=host.ssh('python3 -c '+shlex.quote(code),input=archive.read_bytes(),timeout=30)
print(q.stdout.decode())
report=dict(stage=305,original_phone_module_and_loaded_note_match=True,rollback_copied_to_host=True,
            original_sha256=proof['original_sha256'],new_sha256=build['module_sha256'],
            new_note_sha256=hashlib.sha256(note(module.read_bytes())).hexdigest(),files=manifest,not_installed=True)
(HERE/'module-stage-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
