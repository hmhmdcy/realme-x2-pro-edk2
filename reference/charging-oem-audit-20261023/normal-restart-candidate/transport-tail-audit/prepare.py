"""Create an unrun restart tail candidate; never operate a handset."""
from pathlib import Path
import ast,difflib,hashlib,json
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'r7-restart-review.py'
raw=BASE.read_bytes();assert hashlib.sha256(raw).hexdigest()=='1b246fce07f0a012dbde7830b48d4209e258599ebd9c3bf1032d5f793f493f0f'
old=raw.decode();new=old
setup=" libc=ctypes.CDLL(None,use_errno=True);libc.syscall.restype=ctypes.c_long;libc.syscall.argtypes=[ctypes.c_long,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_void_p]\n command=ctypes.create_string_buffer(b'bootloader\\0')\n"
assert new.count(setup)==1
new=new.replace(setup,'',1)
new=new.replace('try:\n with mmap.mmap',setup.replace('\n ','\n').lstrip()+'try:\n with mmap.mmap',1)
oldtail="  record.update(state='before_single_restart2_bootloader',eud_console_unbound=True,eud_disable_readback=True);phase.write_text(json.dumps(record)+'\\n');print(json.dumps(record),flush=True)\n time.sleep(0.5);result=libc.syscall(142,0xfee1dead,672274793,0xa1b2c3d4,ctypes.cast(command,ctypes.c_void_p))\n raise RuntimeError('Restart2 bootloader returned: '+str((result,ctypes.get_errno())))"
newtail="  # After retirement, transport output, JSON writes, sleep and mmap close\n  # must not stand between the confirmed CSR readback and this one syscall.\n  result=libc.syscall(142,0xfee1dead,672274793,0xa1b2c3d4,ctypes.cast(command,ctypes.c_void_p))\n  raise RuntimeError('Restart2 bootloader returned: '+str((result,ctypes.get_errno())))"
assert new.count(oldtail)==1
new=new.replace(oldtail,newtail,1)
new=new.replace("state='filesystem_frozen',restart2_bootloader=True", "state='filesystem_frozen_restart2_armed',restart2_bootloader=True",1)
new=new.replace('# REVIEW CANDIDATE ONLY. Fresh current-boot guard; no hot module replacement.',
 '# UNRUN TRANSPORT-TAIL REVIEW CANDIDATE. Never repeat the existing R7 transaction.',1)
ast.parse(new)
target=HERE/'r7-restart-transport-tail-review.py';target.write_text(new,encoding='utf-8',newline='\n')
(HERE/'transport-tail.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile=BASE.name,tofile=target.name)),encoding='utf-8',newline='\n')
result={'base_sha256':hashlib.sha256(raw).hexdigest(),'candidate_sha256':hashlib.sha256(new.encode()).hexdigest(),
 'candidate_executed':False,'device_access':False,'existing_transaction_must_not_be_retried':True}
(HERE/'generation-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
