"""Actual Unix temp-file modes and third-file failure/restore, no phone access."""
from pathlib import Path
import hashlib,importlib.util,json,os,stat,tempfile,types
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('profile_permission_adapter',HERE/'host.py');a=importlib.util.module_from_spec(s);s.loader.exec_module(a);u=a.u
path=u.OUT/'stage-worker.py';original=path.read_bytes();w=u.load(path,'profile_permission_actual_worker')
sha=lambda raw:hashlib.sha256(raw).hexdigest()
with tempfile.TemporaryDirectory(prefix='three-file-modes-') as name:
 root=Path(name);paths=[root/'protection.ko',root/'samurai-charging',root/'manifest.json']
 modes=[0o600,0o755,0o600];old=[b'old-module',b'#!/bin/sh\nexit 0\n',b'old-manifest'];new=[b'new-module',b'#!/bin/sh\nexit 7\n',b'new-manifest']
 w.ORDER=[str(p) for p in paths];w.MODES={str(p):m for p,m in zip(paths,modes)};w.OLD_FILES={str(p):sha(b) for p,b in zip(paths,old)};w.NEW_FILES={str(p):sha(b) for p,b in zip(paths,new)}
 for p,raw,mode in zip(paths,old,modes):p.write_bytes(raw);p.chmod(mode)
 events=[];device=types.SimpleNamespace(request={'transaction_id':'offline-mode-test'},read_owned=w.read_owned,event=events.append)
 for p,raw in zip(paths,new):w.Device.replace(device,str(p),raw)
 assert all(p.read_bytes()==raw and stat.S_IMODE(p.stat().st_mode)==mode for p,raw,mode in zip(paths,new,modes));assert os.access(paths[1],os.X_OK)
 for p,raw in zip(paths,old):w.Device.replace(device,str(p),raw,restore=True)
 assert all(p.read_bytes()==raw and stat.S_IMODE(p.stat().st_mode)==mode for p,raw,mode in zip(paths,old,modes))
 actual=w.atomic_replace
 class FailManifest:
  def __getattr__(self,key):return getattr(os,key)
  def replace(self,src,dst):
   if Path(dst)==paths[2]:raise OSError(5,'injected third-file rename failure')
   return os.replace(src,dst)
 def faulted(*args,**kw):return actual(*args,**kw,ops=FailManifest())
 w.atomic_replace=faulted;device.request={'transaction_id':'offline-third-file-failure'}
 caught=False
 try:
  for p,raw in zip(paths,new):w.Device.replace(device,str(p),raw)
 except w.AtomicFailure as error:assert error.stage=='rename';caught=True
 assert caught and paths[0].read_bytes()==new[0] and paths[1].read_bytes()==new[1] and paths[2].read_bytes()==old[2]
 w.atomic_replace=actual
 for p,raw in zip(paths,old):w.Device.replace(device,str(p),raw,restore=True)
 assert all(p.read_bytes()==raw and stat.S_IMODE(p.stat().st_mode)==mode for p,raw,mode in zip(paths,old,modes));assert os.access(paths[1],os.X_OK)
 retained=list(root.glob('.*.next'));assert len(retained)==1 and retained[0].read_bytes()==new[2]
assert path.read_bytes()==original
result=dict(passed=True,actual_Unix_modes=[oct(m) for m in modes],forward_and_inverse_mode_roundtrip=True,third_file_rename_failure_and_exact_original_restore=True,
 failed_temporary_retained_as_evidence=True,production_stage_source_unchanged=True,tested_worker_sha256=sha(original),phone_accessed=False)
u.save(HERE/'permission-check-result.json',result);print(json.dumps(result))
