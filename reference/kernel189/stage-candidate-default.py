"""Stage the compatible module for next boot; never unload a live RPC driver."""
from pathlib import Path
import hashlib,json
import host

candidate=host.PRIVATE/'fastrpc-k189-private.ko'
report=json.loads((Path(__file__).resolve().parent/'fastrpc-module-build-validation.json').read_text())
assert hashlib.sha256(candidate.read_bytes()).hexdigest()==report['candidate_sha256']
host.upload(candidate,'/var/lib/samurai/k189-tools/fastrpc-freezer-candidate.ko')
code='''from pathlib import Path
import hashlib,json,os,shutil,struct
os.umask(0o077)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k189-reboot-runtime/boot-id-private.txt').read_bytes()
assert Path('/sys/class/remoteproc/remoteproc0/state').read_text().strip()=='offline'
assert Path('/sys/devices/platform/sensor-power/state').read_text().strip()=='vdd=0 vddio=0'
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
out=Path('/var/lib/samurai/k189-module-deploy');assert not out.exists();out.mkdir(mode=0o700)
target=Path('/usr/lib/modules')/os.uname().release/'kernel/drivers/misc/fastrpc.ko'
assert hashlib.sha256(target.read_bytes()).hexdigest()=='4515b1b22f212ce2ec482039343d9b72193ef2100e8b0b97227bdde2f37156aa'
old=out/'fastrpc-original-private.ko';shutil.copy2(target,old)
note=Path('/sys/module/fastrpc/notes/.note.gnu.build-id').read_bytes()
data=target.read_bytes();off=struct.unpack_from('<Q',data,40)[0];size,count,idx=struct.unpack_from('<HHH',data,58)
rows=[struct.unpack_from('<IIQQQQIIQQ',data,off+i*size) for i in range(count)]
strings=data[rows[idx][4]:rows[idx][4]+rows[idx][5]]
record=next(r for r in rows if strings[r[0]:].split(b'\\0',1)[0]==b'.note.gnu.build-id')
assert note==data[record[4]:record[4]+record[5]]
candidate=Path('/var/lib/samurai/k189-tools/fastrpc-freezer-candidate.ko')
assert hashlib.sha256(candidate.read_bytes()).hexdigest()=='CANDIDATE_SHA'
temporary=target.with_name('fastrpc.ko.k189-candidate');assert not temporary.exists()
shutil.copyfile(candidate,temporary);temporary.chmod(target.stat().st_mode&0o777);temporary.replace(target)
assert Path('/sys/module/fastrpc/notes/.note.gnu.build-id').read_bytes()==note
summary=dict(stage=189,default_module_candidate_staged=True,old_module_still_loaded=True,
 candidate_sha256='CANDIDATE_SHA',original_sha256='4515b1b22f212ce2ec482039343d9b72193ef2100e8b0b97227bdde2f37156aa',
 original_module_backed_up=True,no_module_unload_or_dsp_restart_performed=True,native_candidate_test_passed=False)
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\\n');print(json.dumps(summary))
'''.replace('CANDIDATE_SHA',report['candidate_sha256'])
p=host.ssh('python3 -',input=code.encode());(host.PRIVATE/'module-staging-host-private.log').write_bytes(p.stdout+p.stderr)
(Path(__file__).resolve().parent/'module-staging-validation.json').write_bytes(p.stdout)
print(p.stdout.decode())
