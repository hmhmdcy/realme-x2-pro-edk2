"""Reuse exact numeric evidence: no focus/workspace/AF/tone code changed."""
from pathlib import Path
import hashlib,json,re,shutil,subprocess,tempfile
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;volume=storage.mount.mounted_build().parent
tree=storage.candidate()/'src/libcamera-v0.7.2';old=volume/'libcamera446-focus-workspace/src/libcamera-v0.7.2'
state=json.loads((HERE/'source-state.json').read_text());baseline=json.loads((HERE.parent/'kernel446/source-state.json').read_text());changed=set(state['changed_this_stage']);assert len(changed)==2
for row in baseline['source_hashes']:
 if row['path'] not in changed:assert hashlib.sha256((tree/row['path']).read_bytes()).hexdigest()==row['sha256']
name='src/libcamera/pipeline/camss-vfe/hardware_focus.h';a=(old/name).read_text();b=(tree/name).read_text()
assert a[a.index('struct LumaFocusWorkspace {'):a.index('struct FocusMeasurementTiming {')]==b[b.index('struct LumaFocusWorkspace {'):b.index('struct FocusExecutionSnapshot {')]
for name in ['include/libcamera/internal/software_isp/focus_stats.h','src/ipa/libipa/contrast_af.h']:assert (tree/name).read_bytes()==(old/name).read_bytes()
with tempfile.TemporaryDirectory(prefix='source-replay-',dir=P) as work:
 root=Path(work)
 for name in changed:
  p=root/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(old/name,p)
 q=subprocess.run(['patch','-p1','--batch','--fuzz=0','-i',str(HERE/'0059-camss-focus-execution-observations.patch')],cwd=root,capture_output=True)
 (P/'patch-replay.log').write_bytes(q.stdout+q.stderr);assert not q.returncode and not re.search(rb'offset|fuzz',q.stdout+q.stderr,re.I)
 assert all((root/name).read_bytes()==(tree/name).read_bytes() for name in changed)
assert json.loads((HERE.parent/'kernel446/focus-validation.json').read_text())['passed']
r=dict(stage=447,diagnostic_only=True,only_timing_fields_snapshots_and_log_added=True,patch_zero_fuzz_offset_and_source_equal=True,luma_workspace_and_statistics_source_byte_identical446=True,fom_af_state_and_ipa_sources_unchanged=True,retained446_host_sanitizers_and_actual_arm_numeric_proof_reused=True,phone_accessed=False,passed=True)
(HERE/'source-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
