from pathlib import Path
import json
import host
code=r'''
from pathlib import Path
import hashlib,json,os,struct,subprocess
def note(p):
 b=Path(p).read_bytes();offset=struct.unpack_from('<Q',b,40)[0];size,count,index=struct.unpack_from('<HHH',b,58)
 sec=[struct.unpack_from('<IIQQQQIIQQ',b,offset+i*size) for i in range(count)];names=b[sec[index][4]:sec[index][4]+sec[index][5]]
 return next(b[s[4]:s[4]+s[5]] for s in sec if names[s[0]:].split(b'\0',1)[0]==b'.note.gnu.build-id')
p=Path(subprocess.check_output(['modinfo','-n','fastrpc'],text=True).strip());loaded=Path('/sys/module/fastrpc')
log=subprocess.check_output(['dmesg']).decode(errors='replace')
print(json.dumps(dict(module_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),loaded=loaded.exists(),loaded_note_matches_disk=loaded.exists() and (loaded/'notes/.note.gnu.build-id').read_bytes()==note(p),
 dmesg_lines=[l for l in log.splitlines() if any(s in l.lower() for s in ['fastrpc','slpi','ssc','sdsp'])],
 devices={p.name:dict(mode=oct(p.stat().st_mode&0o777),uid=p.stat().st_uid,gid=p.stat().st_gid) for p in Path('/dev').glob('fastrpc*')})))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=25);(host.PRIVATE/'fastrpc-first-boot-private.json').write_bytes(q.stdout)
print(json.dumps(json.loads(q.stdout),indent=2))
