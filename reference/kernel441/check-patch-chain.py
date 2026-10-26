"""Replay just the changed pipeline files from the preserved 440 source."""
from pathlib import Path
import hashlib,json,shutil,subprocess,tempfile
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;v=storage.mount.mounted_build().parent
state=json.loads((HERE/'source-state.json').read_text());old=v/'libcamera440-release-r32/src/libcamera-v0.7.2';tree=storage.candidate()/'src/libcamera-v0.7.2'
with tempfile.TemporaryDirectory(prefix='camss441-replay-',dir=v/'tmp') as temp:
 root=Path(temp)
 for rel in state['changed_paths']:
  if not (old/rel).exists():continue
  p=root/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(old/rel,p)
 for name in ['0052-camss-variable-pd10-geometry.patch','0053-camss-finish-stop-reentry.patch']:
  q=subprocess.run(['patch','-p1','--batch','--fuzz=0','-i',str(HERE/name)],cwd=root,capture_output=True)
  log=q.stdout+q.stderr;(P/(name+'-replay.log')).write_bytes(log)
  assert not q.returncode and b'offset' not in log and b'fuzz' not in log,log.decode()
 for rel in state['changed_paths']:assert (root/rel).read_bytes()==(tree/rel).read_bytes(),rel
kernel=json.loads((HERE/'kernel-source-state.json').read_text());ks=v/'source354'
with tempfile.TemporaryDirectory(prefix='camss441-kernel-replay-',dir=v/'tmp') as temp:
 root=Path(temp)
 for row in kernel['source_hashes']:
  rel=row['path'];p=root/rel;p.parent.mkdir(parents=True,exist_ok=True)
  p.write_bytes(subprocess.check_output(['git','-C',str(ks),'show',kernel['parent_commit']+':'+rel]))
 for name in ['variable-pd10-kernel.patch','sof-queue-diagnostic.patch','aux-restart-sof.patch']:
  q=subprocess.run(['patch','-p1','--batch','--fuzz=0','-i',str(HERE/name)],cwd=root,capture_output=True)
  log=q.stdout+q.stderr;(P/(name+'-replay.log')).write_bytes(log)
  assert not q.returncode and b'offset' not in log and b'fuzz' not in log,log.decode()
 for row in kernel['source_hashes']:assert (root/row['path']).read_bytes()==(ks/row['path']).read_bytes(),row['path']
r=dict(stage=441,preserved440_baseline=True,patches=['0052','0053'],kernel_patches=['variable-pd10-kernel','sof-queue-diagnostic','aux-restart-sof'],rejected_statistics_experiment_not_applied=True,changed_files=len(state['changed_paths']),kernel_changed_files=len(kernel['source_hashes']),zero_fuzz_and_offset=True,replayed_files_match_current_source=True,phone_accessed=False,passed=True)
(HERE/'patch-chain-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
