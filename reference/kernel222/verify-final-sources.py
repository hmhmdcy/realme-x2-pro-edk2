from pathlib import Path
import hashlib,json,stat,subprocess
here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel222');kernel=Path('/home/cy122/pmos-samurai-kernel136/kernel')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for p in here.glob('*.py'):compile(p.read_text(),str(p),'exec')
source=json.loads((here/'sof-candidate-source-validation.json').read_text());build=json.loads((here/'sof-candidate-build-validation.json').read_text())
assert sha(here/'camss-sm8150-sof-candidate.patch')==source['patch_sha256']
assert all(sha(kernel/n)==h for n,h in source['original_sources_sha256'].items())
assert all(sha(private/'sof-candidate-source'/n)==h for n,h in source['candidate_sources_sha256'].items())
assert sha(private/'qcom-camss-sof222.ko')==build['compiled_module_sha256'] and build['checkpatch_exit']==0
replay=private/'sof-patch-replay'
if not replay.exists():
 replay.mkdir(mode=0o700)
 for name in source['original_sources_sha256']:
  p=replay/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((private/'kernel-before-sof'/name).read_bytes())
 p=subprocess.run(['patch','--batch','--forward','-p1','-i',str(here/'camss-sm8150-sof-candidate.patch')],cwd=replay,capture_output=True);(private/'sof-patch-replay-private.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0
assert all(sha(replay/n)==h for n,h in source['candidate_sources_sha256'].items())
snapshot=private/'kernel-before-sof-r2';protected=[p for p in snapshot.rglob('*') if p.is_file()]
assert len(protected)==180
mode_manifest=json.loads((private/'kernel-before-sof-r2-mode-manifest-private.json').read_text())
assert mode_manifest['mode_manifest_captured_after_successful_original_mode_restoration'] and mode_manifest['ntfs_snapshot_modes_not_authoritative']
assert all((kernel/p.relative_to(snapshot)).read_bytes()==p.read_bytes() for p in protected)
assert all(sha(kernel/name)==item['sha256'] and stat.S_IMODE((kernel/name).stat().st_mode)==item['mode'] for name,item in mode_manifest['files'].items())
assert sha(kernel/'drivers/media/i2c/imx471.c')=='cc7562794d1a9b69a0bf7e98f7ed8fcb9e9917b7a6a5c46b833f649a8c60b175'
assert len((kernel/'Module.symvers').read_text().splitlines())==16798
status=subprocess.check_output(['git','status','--porcelain=v1','--untracked-files=normal'],cwd=kernel).decode().splitlines();(private/'kernel-final-status-private.txt').write_text('\n'.join(status)+'\n')
tracked=sum(not x.startswith('??') for x in status);untracked=sum(x.startswith('??') for x in status);assert (tracked,untracked)==(25,11),(tracked,untracked)
diff=subprocess.run(['git','diff','--check'],cwd=kernel,capture_output=True);(private/'kernel-final-diff-private.log').write_bytes(diff.stdout+diff.stderr);assert diff.returncode==0
public_sources=json.loads((here/'sof-public-source-validation.json').read_text())
for name,item in public_sources['files'].items():
 if item['fetched']:assert sha(private/'sof-public-source'/name)==item['sha256']
lock=json.loads((repo/'linux-port/packages/libcamera/source-lock.json').read_text());assert lock['new_recipe_version']=='99990.7.2-r7'
assert all(sha(repo/'linux-port/packages/libcamera'/name)==digest for name,digest in lock['source_files_sha256'].items())
assert sha(here/'request-gap-probe.cpp')==json.loads((here/'gap-probe-build-validation.json').read_text())['source_sha256']
health=json.loads((here/'final-health-validation.json').read_text());assert health['camera_metadata_captures_performed'] and health['original_camss_file_and_loaded_note_verified'] and health['taint']==0
assert 'no_camera_capture_or_engine_start_or_reboot' not in health
event=json.loads((here/'sof-event-analysis-validation.json').read_text());assert event['frame_sync_events']==105 and event['consecutive_frame_sequence'] and event['consecutive_queue_sequence'] and event['metadata_mapping_not_yet_fixed']
assert json.loads((here/'final-evidence-validation.json').read_text())['verified_members']==71
assert (repo/'NEXT-SESSION.md').stat().st_size<=6500
r=dict(stage=222,python_sources_compile=len(list(here.glob('*.py'))),sof_patch_replay_exact=True,candidate_module_and_source_hashes_exact=True,canonical_kernel_original_files_and_modes_restored=180,ntfs_modes_checked_using_explicit_json_not_mount_emulation=True,mode_manifest_captured_after_builder_verified_original_modes=True,original_tracked_modified_files=tracked,original_untracked_entries=untracked,host_imx471_source_still216=True,module_symbols_restored=16798,kernel_diff_check_exit=0,retained_current_r7_recipe_inputs_exact=True,next_session_bytes=(repo/'NEXT-SESSION.md').stat().st_size,goal_active=True)
(here/'source-final-validation.json').write_text(json.dumps(r,indent=2)+'\n')
final=dict(stage=222,request_gap_frame_association_defect_reproduced=True,standard_frame_sync_candidate_physically_verified=True,consecutive_sof_events=105,client_metadata_requests=48,product_driver_and_userland_restored=True,candidate_not_permanently_deployed=True,manual_api_and_buffer_sof_pairing_still_open=True,native_archive_members=71,full_peripheral_goal_active=True)
(here/'final-validation.json').write_text(json.dumps(final,indent=2)+'\n');print(json.dumps(r))
