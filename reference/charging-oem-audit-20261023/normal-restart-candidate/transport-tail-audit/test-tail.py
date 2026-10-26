"""Actual CPython EPIPE and actual worker AST tail with only fake boundaries."""
from pathlib import Path
import ast,contextlib,ctypes,errno,hashlib,io,json,os,struct,subprocess,sys,types
HERE=Path(__file__).resolve().parent
old=(HERE.parent/'r7-restart-review.py').read_text()
new=(HERE/'r7-restart-transport-tail-review.py').read_text()

# Real interpreter, real anonymous pipe with its only reader closed. Neither
# this experiment nor the extracted worker tests use a hardware/SSH endpoint.
reader,writer=os.pipe();os.close(reader)
child=r'''import json,os,signal
try:
 print('post-retirement output',flush=True)
except Exception as e:
 os.write(2,json.dumps(dict(type=type(e).__name__,errno=e.errno,
  is_exception=isinstance(e,Exception),sigpipe_ignored=signal.getsignal(signal.SIGPIPE)==signal.SIG_IGN)).encode())
 os._exit(0)
os._exit(9)
'''
try:q=subprocess.run([sys.executable,'-c',child],stdout=writer,stderr=subprocess.PIPE,timeout=5)
finally:os.close(writer)
pipe=json.loads(q.stderr)
assert q.returncode==0 and pipe==dict(type='BrokenPipeError',errno=32,is_exception=True,sigpipe_ignored=True)

class RestartTransferred(BaseException):pass

def exercise(source,injection=None,returns=False):
 tree=ast.parse(source)
 tail=next(node for node in tree.body if isinstance(node,ast.Try))
 events=[];image=bytearray(4096);struct.pack_into('<I',image,0x14,1)
 state={'unbound':False,'syscalls':0,'thaws':0,'outcome':None}
 class Mapping:
  def __enter__(self):return image
  def __exit__(self,*args):events.append('mmap_close')
 class FakePhase:
  def open(self,mode):events.append('claim');return io.StringIO()
  def write_text(self,text):
   events.append('phase_after_retirement' if image[0x14]==0 else 'phase_before_retirement')
   if injection=='phase_after_retirement' and image[0x14]==0:raise OSError(errno.ENOSPC,'fixture tmpfs full')
 class Driver:
  def exists(self):return not state['unbound']
 class Device:
  name='88e0000.serial'
  def __truediv__(self,key):assert key=='driver';return Driver()
 class FakePath:
  def __init__(self,path):assert path=='/sys/bus/platform/drivers/qcom_eud_com/unbind'
  def write_text(self,text):assert text=='88e0000.serial';state['unbound']=True;events.append('unbind')
 def output(*args,**kwargs):
  retired=image[0x14]==0;events.append('print_after_retirement' if retired else 'print_before_retirement')
  if injection=='stdout_after_retirement' and retired or injection=='stdout_before_retirement' and not retired:
   raise BrokenPipeError(errno.EPIPE,'fixture closed SSH output')
 def ioctl(fd,command,value):
  if command==0xc0045877:events.append('freeze')
  else:assert command==0xc0045878;state['thaws']+=1;events.append('thaw')
 def syscall(*args):
  assert args[0]==142 and args[3]==0xa1b2c3d4
  state['syscalls']+=1;events.append('syscall142')
  if not returns:raise RestartTransferred()
  return -1
 fake_lib=types.SimpleNamespace(syscall=syscall)
 native=types.SimpleNamespace(CDLL=lambda *args,**kwargs:fake_lib,c_long=ctypes.c_long,
  c_ulong=ctypes.c_ulong,c_void_p=ctypes.c_void_p,create_string_buffer=ctypes.create_string_buffer,
  cast=ctypes.cast,get_errno=lambda:5)
 fake_struct=types.SimpleNamespace(unpack_from=struct.unpack_from,pack_into=struct.pack_into)
 if injection=='csr_readback_failure':fake_struct.pack_into=lambda *args:None
 env=dict(fd=101,rootfd=None,frozen=False,phase=FakePhase(),device=Device(),
  meta=dict(transaction_id='new-future-fixture',boot_id='fixture'),Path=FakePath,
  mmap=types.SimpleNamespace(mmap=lambda *args,**kwargs:Mapping(),MAP_SHARED=1,PROT_READ=1,PROT_WRITE=2),
  os=types.SimpleNamespace(open=lambda *args:202,O_RDONLY=0,O_DIRECTORY=1,sync=lambda:events.append('sync'),close=lambda fd:events.append('close_fd')),
  sys=types.SimpleNamespace(argv=['worker','--guard','guard','--commit-restart2-bootloader']),
  fcntl=types.SimpleNamespace(ioctl=ioctl),struct=fake_struct,json=json,print=output,
  time=types.SimpleNamespace(sleep=lambda seconds:events.append('sleep')),ctypes=native)
 # Candidate intentionally moves this setup outside the try before freeze.
 if 'libc' not in env:env['libc']=fake_lib;env['command']=ctypes.create_string_buffer(b'bootloader\0')
 try:exec(compile(ast.Module(body=[tail],type_ignores=[]),'actual-worker-tail','exec'),env)
 except RestartTransferred:state['outcome']='simulated nonreturn'
 except Exception as e:state['outcome']=type(e).__name__
 state['csr_low_byte']=image[0x14];state['events']=events
 return state

rows=[]
for label,src,inj,returns,calls,thaws in [
 ('old normal',old,None,False,1,0),
 ('old post-CSR EPIPE prevents syscall',old,'stdout_after_retirement',False,0,1),
 ('old post-CSR phase ENOSPC prevents syscall',old,'phase_after_retirement',False,0,1),
 ('new post-CSR stdout cannot prevent syscall',new,'stdout_after_retirement',False,1,0),
 ('new post-CSR phase write eliminated',new,'phase_after_retirement',False,1,0),
 ('new pre-retirement EPIPE aborts before unbind',new,'stdout_before_retirement',False,0,1),
 ('new failed CSR readback still blocks reboot',new,'csr_readback_failure',False,0,1),
 ('new returned syscall still thaws and fails',new,None,True,1,1)]:
 row=exercise(src,inj,returns);assert row['syscalls']==calls and row['thaws']==thaws,(label,row)
 if label.startswith('new post-CSR'):
  assert 'print_after_retirement' not in row['events'] and 'phase_after_retirement' not in row['events']
  assert row['events'].index('syscall142')<row['events'].index('mmap_close')
 if 'pre-retirement EPIPE' in label:assert not row['unbound'] and row['csr_low_byte']==1
 row['label']=label;rows.append(row)
result=dict(passed=True,actual_cpython_pipe=pipe,interpreter=sys.version,
 actual_worker_ast_boundary_cases=rows,candidate_sha256=hashlib.sha256(new.encode()).hexdigest(),
 device_access=False,actual_reboot=False,current_incident_root_cause_proven=False)
(HERE/'test-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(passed=True,actual_cpython_pipe=pipe,actual_worker_ast_boundary_cases=len(rows),
 candidate_sha256=result['candidate_sha256'],current_incident_root_cause_proven=False),indent=2))
