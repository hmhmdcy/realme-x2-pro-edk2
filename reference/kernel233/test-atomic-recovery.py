"""Exercise actual staging I/O helpers at write, replace and post-rename faults."""
from pathlib import Path
import ast,json,os,tempfile
from unittest.mock import patch
R=Path(__file__).resolve().parent
tree=ast.parse((R/'install-modules.py').read_text())
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['sync_directory','atomic']]
assert len(nodes)==2
ns=dict(Path=Path,os=os,tempfile=tempfile);exec(compile(ast.Module(body=nodes,type_ignores=[]),'actual-io-functions','exec'),ns)
atomic=ns['atomic'];cases=0
with tempfile.TemporaryDirectory(prefix='pmic233-io-') as name:
 d=Path(name);target=d/'module.ko';target.write_bytes(b'old')
 for failure in ['fchmod','replace','directory_fsync']:
  target.write_bytes(b'old');real_chmod=os.fchmod;real_replace=os.replace;real_fsync=os.fsync;calls=[0]
  def bad_chmod(*args):raise OSError('injected pre-rename metadata failure')
  def bad_replace(*args):raise OSError('injected rename failure')
  def bad_sync(fd):
   calls[0]+=1
   if calls[0]==2:raise OSError('injected post-rename directory sync failure')
   return real_fsync(fd)
  op={'fchmod':('fchmod',bad_chmod),'replace':('replace',bad_replace),'directory_fsync':('fsync',bad_sync)}[failure]
  try:
   with patch.object(os,*op):atomic(target,b'candidate',uid=os.getuid(),gid=os.getgid())
  except OSError:pass
  else:raise AssertionError('Fault did not fire')
  assert list(d.iterdir())==[target],'Temporary file leaked'
  assert target.read_bytes()==(b'candidate' if failure=='directory_fsync' else b'old')
  atomic(target,b'old',uid=os.getuid(),gid=os.getgid());assert target.read_bytes()==b'old';cases+=1
report=dict(stage=233,actual_atomic_helpers_tested=True,injected_io_failures=cases,
 own_temporary_files_cleaned=True,rollback_can_replace_after_pre_and_post_rename_failure=True,no_device_access=True)
(R/'atomic-recovery-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
