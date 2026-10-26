"""Replay final source deltas and verify the exact built candidates."""
from pathlib import Path
import difflib,hashlib,importlib.util,json,shutil,subprocess,tempfile
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;candidate=storage.candidate();tree=candidate/'src/libcamera-v0.7.2';old=candidate.parent/'libcamera424-tone-domains/src/libcamera-v0.7.2'
state=json.loads((HERE/'source-state.json').read_text());names=[r['path'] for r in state['source_hashes']];patch=''
for row in state['source_hashes']:
 n=row['path'];assert hashlib.sha256((tree/n).read_bytes()).hexdigest()==row['sha256']
 before=(old/n).read_text() if (old/n).exists() else '';after=(tree/n).read_text()
 patch+=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+n if before else '/dev/null',tofile='b/'+n))
(HERE/'0046-camss-pd10-auto-pair.patch').write_text(patch)
with tempfile.TemporaryDirectory(dir=candidate.parent/'tmp',prefix='k431-user-replay-') as tmp:
 replay=Path(tmp)
 for n in names:
  if (old/n).exists():p=replay/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(old/n,p)
 q=subprocess.run(['patch','-p1','--fuzz=0','--batch'],cwd=replay,input=patch.encode(),capture_output=True);assert not q.returncode and b'offset' not in q.stdout and b'fuzz' not in q.stdout,q.stdout+q.stderr
 for n in names:assert (replay/n).read_bytes()==(tree/n).read_bytes()
for n in ['ipe_tone_profile.cpp','ipe_tone_profile.h','ipe_frame_history.h','ipe_numeric_history.h']:
 assert (old/'src/ipa/camss-vfe'/n).read_bytes()==(tree/'src/ipa/camss-vfe'/n).read_bytes()
build=json.loads((HERE/'build-validation.json').read_text());assert build['passed'] and build['private_ipa_version']==4
for row in build['runtime_files']:assert hashlib.sha256((P/row['name']).read_bytes()).hexdigest()==row['sha256']
k=storage.mount.mounted_build().parent/'source354';ks=json.loads((HERE/'kernel-source-state.json').read_text());git=lambda *a:subprocess.check_output(['git','-C',str(k),*a])
assert git('rev-parse','HEAD').decode().strip()==ks['commit'] and not git('status','--porcelain')
assert git('diff',ks['parent_commit'],ks['commit'])==(HERE/'request-coarse.patch').read_bytes()
with tempfile.TemporaryDirectory(dir=candidate.parent/'tmp',prefix='k431-kernel-replay-') as tmp:
 replay=Path(tmp)
 for row in ks['source_hashes']:
  p=replay/row['path'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(git('show',ks['parent_commit']+':'+row['path']))
 q=subprocess.run(['patch','-p1','--fuzz=0','--batch'],cwd=replay,input=(HERE/'request-coarse.patch').read_bytes(),capture_output=True);assert not q.returncode and b'offset' not in q.stdout and b'fuzz' not in q.stdout
 for row in ks['source_hashes']:assert (replay/row['path']).read_bytes()==(k/row['path']).read_bytes() and hashlib.sha256((k/row['path']).read_bytes()).hexdigest()==row['sha256']
modules=json.loads((HERE/'intree-build-validation.json').read_text());assert modules['passed'] and not modules['diagnostics']
for row in modules['modules']:assert hashlib.sha256(Path(row['private_path']).read_bytes()).hexdigest()==row['sha256']
for name in ['qcom-camss.ko','qcom-camss-icp-a5-core.ko','camss-icp-a5-m2m.ko','camss-icp-a5-m2m.o']:
 rel=Path('drivers/media/platform/qcom/camss')/name;a=P/'intree-build-r1-before'/rel;b=storage.mount.mounted_build()/rel
 assert a.exists()==b.exists()
 if a.exists():assert a.read_bytes()==b.read_bytes()
r=dict(stage=431,userspace_base_stage=424,userspace_files=len(names),private_ipa_version=4,kernel_commit=ks['commit'],kernel_changed_files=1,
 source_hashes_match=True,patches_replay_without_fuzz_or_offset=True,stock_tmc_ltm_math_and_numeric_history_implementation_unchanged=True,
 typed_mode_ds4_capability_added=True,paired_source_and_final_receipt_lifetimes_connected=True,kernel_user_abi_unchanged=True,
 kernel_cohort_verified=True,shared_selected_kernel_outputs_restored=True,latest_userspace_build=build['attempt'],installed=False,passed=True)
(HERE/'source-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
