from pathlib import Path
import base64,hashlib,json
import host
R=Path(__file__).resolve().parent;P=host.PRIVATE
assert not json.loads((P/'quiesce-submission-inspection-private.json').read_text())['worker_context_exists']
backup=P/'transition-before-guard-correction';backup.mkdir(mode=0o700);args={}
for name in ['native-quiesce.py','restart-bootloader.py','launch-quiesce.py','poll-quiesce.py','submit-restart.py','flash-boot.py']:
 p=R/name;old=p.read_bytes();(backup/name).write_bytes(old);new=old.replace(b'k273-work',b'k275-work');p.write_bytes(new);compile(new,name,'exec')
 if name in ['native-quiesce.py','restart-bootloader.py']:args[name]=dict(before_sha256=hashlib.sha256(old).hexdigest(),data=base64.b64encode(new).decode())
code=r'''
from pathlib import Path
import base64,hashlib,json
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k275-work/boot-id-private.txt').read_bytes()
assert not (r/'k276-quiesce').exists()
for name,row in args.items():
 p=r/'k276-tools'/name;old=p.read_bytes();assert hashlib.sha256(old).hexdigest()==row['before_sha256'];saved=p.with_name(name+'.before-guard-correction');assert not saved.exists();saved.write_bytes(old);data=base64.b64decode(row['data']);compile(data,name,'exec');p.write_bytes(data)
print(json.dumps(dict(stage=276,current_guard_corrected_to275=True,no_quiesce_worker_had_started=True)))
'''
q=host.ssh('python3 -',input=('args='+repr(args)+'\n'+code).encode(),timeout=15);(P/'transition-guard-correction-private.json').write_bytes(q.stdout);print(q.stdout.decode())
