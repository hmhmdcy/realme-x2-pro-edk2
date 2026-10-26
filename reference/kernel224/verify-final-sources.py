from pathlib import Path
import hashlib,json,os,re,shutil,stat,subprocess

here=Path(__file__).resolve().parent;repo=here.parents[1]
private=Path('/mnt/e/edk2-samurai-out/kernel224');previous=private.parent/'kernel223'
kernel=Path('/home/cy122/pmos-samurai-kernel136/kernel');sdk=Path('/home/cy122/x2pro-linux/libcamera214-root')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for p in here.glob('*.py'):compile(p.read_text(),str(p),'exec')

original=json.loads((private/'original214-work-manifest-private.json').read_text());assert len(original)==2254
for n,item in original.items():
 p=sdk/'work/libcamera'/n
 if 'target' in item:assert p.is_symlink() and os.readlink(p)==item['target']
 else:assert not p.is_symlink() and sha(p)==item['sha256'] and stat.S_IMODE(p.stat().st_mode)==item['mode']
assert not list((sdk/'private').glob('libcamera214-before224*'))
for name in ['r9-build-state-private.json','r10-build-state-private.json','r11-build-state-private.json']:
 assert json.loads((private/name).read_text())['terminal']

modes=json.loads((previous/'kernel-before-paired-sof-mode-manifest-before-build-private.json').read_text());assert len(modes)==180
for n,item in modes.items():assert sha(kernel/n)==item['sha256'] and stat.S_IMODE((kernel/n).stat().st_mode)==item['mode']
assert len((kernel/'Module.symvers').read_text().splitlines())==16798
status=subprocess.check_output(['git','status','--porcelain=v1','--untracked-files=normal'],cwd=kernel,text=True).splitlines()
tracked=sum(not l.startswith('??') for l in status);untracked=sum(l.startswith('??') for l in status);assert (tracked,untracked)==(25,11)
(private/'kernel-final-status-private.txt').write_text('\n'.join(status)+'\n')
check=subprocess.run(['git','diff','--check'],cwd=kernel,capture_output=True);(private/'kernel-final-diff-private.log').write_bytes(check.stdout+check.stderr);assert check.returncode==0

recipe=repo/'linux-port/packages/libcamera';lock=json.loads((recipe/'source-lock.json').read_text());assert lock['new_recipe_version']=='99990.7.2-r11'
assert all(sha(recipe/n)==v for n,v in lock['source_files_sha256'].items())
old_lock=json.loads((repo/'reference/kernel223/source-final-validation.json').read_text())
assert old_lock['promoted_recipes_deployment_locks_and_all13_package_hashes_exact']
recipe_before=sdk/'work/libcamera223'
for p in recipe_before.iterdir():
 if p.is_file() and p.suffix in ['.patch','.yaml','.desktop']:assert p.read_bytes()==(recipe/p.name).read_bytes()
checksums=re.findall(r'^([0-9a-f]{128})  (\S+)$',(recipe/'APKBUILD').read_text(),re.M)
local_checks=0
for digest,name in checksums:
 if name=='libcamera-v0.7.2.tar.gz':continue
 assert hashlib.sha512((recipe/name).read_bytes()).hexdigest()==digest;local_checks+=1
assert len(list(recipe.glob('*.patch')))==17

replay=private/'patch-replay-final'
first=json.loads((here/'candidate-source-validation.json').read_text())
source_root=sdk/'work/libcamera223-built/src/libcamera-v0.7.2'
if not replay.exists():
 replay.mkdir(mode=0o700)
 for n,v in first['original_sources_sha256'].items():
  p=source_root/n;assert sha(p)==v;q=replay/n;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
 for name,proof_name in [
  ('0015-simple-raw-only-statistics.patch','candidate-source-validation.json'),
  ('0016-simple-stop-live-requests.patch','stop-fix-source-validation.json'),
  ('0017-simple-capture-cancel-status.patch','cancel-status-source-validation.json')]:
  proof=json.loads((here/proof_name).read_text());assert sha(recipe/name)==proof['patch_sha256']
  assert all(sha(replay/n)==v for n,v in proof['original_sources_sha256'].items())
  p=subprocess.run(['patch','--batch','--forward','-p1','-i',str(recipe/name)],cwd=replay,capture_output=True)
  (private/(name+'.replay-private.log')).write_bytes(p.stdout+p.stderr);assert p.returncode==0
  assert all(sha(replay/n)==v for n,v in proof['source_files'].items())
 expected=dict(first['source_files']);expected.update(json.loads((here/'cancel-status-source-validation.json').read_text())['source_files'])
 (private/'patch-replay-final-state-private.json').write_text(json.dumps(dict(verified=True,expected=expected),indent=2)+'\n')
else:
 state=json.loads((private/'patch-replay-final-state-private.json').read_text());assert state['verified'];expected=state['expected']
assert all(sha(replay/n)==v and sha(sdk/'work/libcamera224-r11-built/src/libcamera-v0.7.2'/n)==v for n,v in expected.items())
assert sha(here/'raw-lifecycle-probe.cpp')=='17d1312fc339107ee7fab90715ad84981bd15ea8f2c3923735add61fc9b14f4f'
kernel_lock=json.loads((repo/'linux-port/camera/kernel/source-lock.json').read_text());assert kernel_lock['stage']==223 and kernel_lock['camss']['module_sha256']=='fae1ed40da4e2751c081aca3a990a5a3c44de47599883a045340b9f62f54803e'

manifest=json.loads((private/'camera-forward-repo-r11/package-manifest.json').read_text());assert len(manifest['packages'])==13
assert all(sha(private/'camera-forward-repo-r11'/p['file'])==p['sha256'] for p in manifest['packages'])
deployment=json.loads((repo/'linux-port/camera/deployment-lock.json').read_text())
assert deployment['framework_version']=='99990.7.2-r11' and deployment['configuration_version']=='0.1.0-r6'
assert deployment['built_packages']==[{k:p[k] for k in ['name','version','file','sha256','bytes']} for p in manifest['packages']]
assert deployment['kernel_image_boot_dtb_and_all_modules_unchanged_in_stage224']
assert json.loads((here/'r11-host-runtime-qa-validation.json').read_text())['all_five_ipa_signatures_valid']
health=json.loads((here/'final-health-validation.json').read_text());assert health['taint']==0 and health['nv_sources_unchanged'] and health['current_policy_r11_library_hashes_verified']
archive=json.loads((here/'final-evidence-validation.json').read_text());assert archive['verified_members']==416 and archive['archive_and_all_member_hashes_verified']
handoff=repo/'NEXT-SESSION.md';assert handoff.stat().st_size<=6500
for required in ['## 源码、产物与回退依据','## 续作与已知风险']:assert required in handoff.read_text()
r=dict(stage=224,python_sources_compile=len(list(here.glob('*.py'))),three_patch_sequential_replay_matches_intermediate_and_final_sources=True,
 original214_files_links_modes_preserved=2254,no_pending_original214_snapshot=True,all_three_builds_terminal=True,
 canonical_kernel_original_files_and_modes_preserved=180,canonical_kernel_symbols_preserved=16798,
 original_kernel_tracked_modified=tracked,original_kernel_untracked_entries=untracked,kernel_diff_check_exit=0,
 mode_comparison_uses_explicit_json_not_ntfs_emulated_modes=True,recipe_patch_count=17,recipe_local_sha512_inputs_verified=local_checks,
 current_recipe_locks_and_all13_packages_exact=True,kernel_source_lock_remains_stage223=True,
 unchanged_lifecycle_probe_source_verified=True,native_archive_members=416,next_session_bytes=handoff.stat().st_size,
 full_peripheral_goal_active=True)
(here/'source-final-validation.json').write_text(json.dumps(r,indent=2)+'\n')
final=dict(stage=224,r11_r6_installed_and_policy_reloaded=True,raw_only_cpu_auto_statistics_and_metadata_enabled=True,
 stop_request_ownership_and_capture_cancel_status_fixed=True,r9_r10_failed_candidates_retained=True,
 r11_candidate_raw_rgb_threaded_isolated_frames=128,installed_default_raw_rgb_threaded_isolated_frames=128,
 installed_experimental_full_raw_metadata_frames=36,installed_experimental_full_rgb_metadata_frames=36,
 lifecycle_candidate_threaded_requests=40,lifecycle_candidate_isolated_requests=40,lifecycle_installed_requests=40,
 lifecycle_each_completed=20,lifecycle_each_cancelled=20,standard_cam_and_gstreamer_frames=12,
 full_mode_disabled_and_devices_suspended=True,taint=0,fault_counts=health['fault_counts'],native_archive_members=416,
 boot_kernel_image_and_driver_modules_unchanged=True,r8_r3_rollback_retained_keeps_fae1_e49=True,
 manual_api_physical_delay_real_colour_geometry_and_rear_cameras_still_open=True,
 gnss_real_fix_and_all_other_peripheral_goal_still_open=True,full_peripheral_goal_active=True)
(here/'final-validation.json').write_text(json.dumps(final,indent=2)+'\n');print(json.dumps(r))
