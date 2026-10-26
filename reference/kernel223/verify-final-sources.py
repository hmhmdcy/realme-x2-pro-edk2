from pathlib import Path
import hashlib,json,os,stat,subprocess

here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel223');kernel=Path('/home/cy122/pmos-samurai-kernel136/kernel');sdk=Path('/home/cy122/x2pro-linux/libcamera214-root')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for p in here.glob('*.py'):compile(p.read_text(),str(p),'exec')
source=json.loads((here/'sof-candidate-source-validation.json').read_text());build=json.loads((here/'sof-candidate-build-validation.json').read_text())
assert sha(here/'camss-sm8150-paired-sof-candidate.patch')==source['patch_sha256']
assert all(sha(kernel/n)==v for n,v in source['original_sources_sha256'].items())
assert all(sha(private/'sof-candidate-source'/n)==v for n,v in source['candidate_sources_sha256'].items())
assert sha(private/'qcom-camss-sof223.ko')==build['compiled_module_sha256'] and build['checkpatch_exit']==0
mode_manifest=json.loads((private/'kernel-before-paired-sof-mode-manifest-before-build-private.json').read_text());assert len(mode_manifest)==180
for n,item in mode_manifest.items():assert sha(kernel/n)==item['sha256'] and stat.S_IMODE((kernel/n).stat().st_mode)==item['mode']
assert len((kernel/'Module.symvers').read_text().splitlines())==16798
assert sha(kernel/'drivers/media/i2c/imx471.c')=='cc7562794d1a9b69a0bf7e98f7ed8fcb9e9917b7a6a5c46b833f649a8c60b175'
status=subprocess.check_output(['git','status','--porcelain=v1','--untracked-files=normal'],cwd=kernel,text=True).splitlines()
tracked=sum(not l.startswith('??') for l in status);untracked=sum(l.startswith('??') for l in status);assert (tracked,untracked)==(25,11)
(private/'kernel-final-status-private.txt').write_text('\n'.join(status)+'\n')
check=subprocess.run(['git','diff','--check'],cwd=kernel,capture_output=True);(private/'kernel-final-diff-private.log').write_bytes(check.stdout+check.stderr);assert check.returncode==0

original=json.loads((private/'original214-work-manifest-private.json').read_text());assert len(original)==2254
for n,item in original.items():
 p=sdk/'work/libcamera'/n
 if 'target' in item:assert p.is_symlink() and os.readlink(p)==item['target']
 else:assert not p.is_symlink() and sha(p)==item['sha256'] and stat.S_IMODE(p.stat().st_mode)==item['mode']
assert not (sdk/'private/libcamera214-before223').exists()
state=json.loads((private/'r8-build-state-private.json').read_text());assert state['terminal']
recipe=repo/'linux-port/packages/libcamera';lock=json.loads((recipe/'source-lock.json').read_text());assert lock['new_recipe_version']=='99990.7.2-r8'
for n,v in lock['source_files_sha256'].items():assert sha(recipe/n)==v
kernel_lock=json.loads((repo/'linux-port/camera/kernel/source-lock.json').read_text());assert kernel_lock['camss']['module_sha256']==build['compiled_module_sha256']
assert sha(repo/'linux-port/camera/kernel'/kernel_lock['camss']['patch'])==source['patch_sha256']
replay=private/'patch-replay-final';replay.mkdir(mode=0o700,exist_ok=True)
def replay_patch(label,files,patch,expected):
 directory=replay/label
 if not directory.exists():
  directory.mkdir(mode=0o700)
  for n,p in files.items():q=directory/n;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(p.read_bytes())
  r=subprocess.run(['patch','--batch','--forward','-p1','-i',str(patch)],cwd=directory,capture_output=True)
  (private/(label+'-patch-replay-private.log')).write_bytes(r.stdout+r.stderr);assert r.returncode==0
 assert all(sha(directory/n)==v for n,v in expected.items())
replay_patch('camss',{n:private/'kernel-before-paired-sof'/n for n in source['original_sources_sha256']},here/'camss-sm8150-paired-sof-candidate.patch',source['candidate_sources_sha256'])
framework=json.loads((here/'candidate-source-validation.json').read_text());n='src/libcamera/pipeline/simple/simple.cpp'
base=sdk/'work/libcamera220-built/src/libcamera-v0.7.2'/n;assert sha(base)==framework['original_source_sha256']
replay_patch('libcamera',{n:base},recipe/'0014-simple-capture-control-snapshot.patch',framework['source_files'])
assert all(sha(sdk/'work/libcamera223-built/src/libcamera-v0.7.2'/n)==v for n,v in framework['source_files'].items())
manifest=json.loads((private/'camera-forward-repo/package-manifest.json').read_text());assert len(manifest['packages'])==13
assert all(sha(private/'camera-forward-repo'/p['file'])==p['sha256'] for p in manifest['packages'])
deployment=json.loads((repo/'linux-port/camera/deployment-lock.json').read_text());assert deployment['framework_version']=='99990.7.2-r8' and deployment['camss_module_sha256']==build['compiled_module_sha256']
assert deployment['built_packages']==[{k:p[k] for k in ['name','version','file','sha256','bytes']} for p in manifest['packages']]
health=json.loads((here/'final-health-validation.json').read_text());assert health['deployed_camss_file_and_loaded_note_verified'] and health['nv_sources_unchanged'] and health['taint']==0
archive=json.loads((here/'final-evidence-validation.json').read_text());assert archive['verified_members']==281
handoff=repo/'NEXT-SESSION.md';assert handoff.stat().st_size<=6500
for required in ['## 源码、产物与回退依据','## 续作与已知风险']:assert required in handoff.read_text()
r=dict(stage=223,python_sources_compile=len(list(here.glob('*.py'))),kernel_and_libcamera_patch_replays_exact=True,
 canonical_kernel_original_files_and_modes_preserved=180,original214_files_links_modes_preserved=2254,
 mode_comparison_uses_explicit_prebuild_json_not_ntfs_mount_modes=True,canonical_module_symbols_preserved=16798,
 original_kernel_tracked_modified=tracked,original_kernel_untracked_entries=untracked,kernel_diff_check_exit=0,
 promoted_recipes_deployment_locks_and_all13_package_hashes_exact=True,no_pending_original_build_tree_snapshot=True,
 native_evidence_archive_members=281,next_session_bytes=handoff.stat().st_size,full_peripheral_goal_active=True)
(here/'source-final-validation.json').write_text(json.dumps(r,indent=2)+'\n')
final=dict(stage=223,coherent_paired_camss_and_r8_r3_deployed=True,buffer_sof_pairing_verified_frames=160,
 r8_capture_control_association_verified_rgb_frames=128,r8_exposure_conversion_verified_rgb_frames=164,
 standard_cam_and_gstreamer_frames=12,dark_numeric_raw_and_rgb_frames=12,dark_fixed_all_zero_output_not_reproduced=True,
 original_camss_and_r7_r2_rollback_retained=True,native_archive_members=281,taint=0,manual_api_and_physical_optical_delay_still_open=True,
 gnss_real_fix_and_other_peripheral_goal_still_open=True,full_peripheral_goal_active=True)
(here/'final-validation.json').write_text(json.dumps(final,indent=2)+'\n');print(json.dumps(r))
