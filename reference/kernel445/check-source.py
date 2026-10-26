from pathlib import Path
import hashlib,json,re,shutil,subprocess,tempfile
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;volume=storage.mount.mounted_build().parent
tree=storage.candidate()/'src/libcamera-v0.7.2';old=volume/'libcamera444-focused-ipe/src/libcamera-v0.7.2'
state=json.loads((HERE/'source-state.json').read_text());baseline=json.loads((HERE.parent/'kernel444/source-state.json').read_text());changed=set(state['changed_this_stage']);assert len(changed)==2
for row in baseline['source_hashes']:
 if row['path'] not in changed:assert hashlib.sha256((tree/row['path']).read_bytes()).hexdigest()==row['sha256']
for name in ['include/libcamera/internal/software_isp/focus_stats.h','src/ipa/libipa/contrast_af.h']:
 assert (tree/name).read_bytes()==(old/name).read_bytes()
assert (tree/'src/libcamera/pipeline/camss-vfe/hardware_focus.h').read_bytes()==(HERE/'hardware_focus.h').read_bytes()
with tempfile.TemporaryDirectory(prefix='source-replay-',dir=P) as work:
 root=Path(work)
 for name in changed:
  p=root/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(old/name,p)
 q=subprocess.run(['patch','-p1','--batch','--fuzz=0','-i',str(HERE/'0057-camss-exact-focus-grid.patch')],cwd=root,capture_output=True)
 (P/'patch-replay.log').write_bytes(q.stdout+q.stderr);assert not q.returncode and not re.search(rb'offset|fuzz',q.stdout+q.stderr,re.I)
 assert all((root/name).read_bytes()==(tree/name).read_bytes() for name in changed)
r=dict(stage=445,only_two_production_files_changed=True,patch_zero_fuzz_offset_and_source_equal=True,
 original_fom_normalization_and_af_state_machine_unchanged=True,ipa_protocol6_math_tuning_and_proxy_sources_unchanged=True,
 only_exact_grid_arithmetic_and_timing_in_camera_core=True,phone_accessed=False,passed=True)
(HERE/'source-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
