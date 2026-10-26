"""Verify current artifacts, source, finished probes, archives and acceptance limits."""
from pathlib import Path
import hashlib,json,subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];P=Path('/mnt/e/edk2-samurai-out/kernel298')
load=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
checkpoint=load(HERE/'checkpoint-validation.json')
for name,row in checkpoint['files'].items():
 p=ROOT/name;assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],name
assert len(checkpoint['files'])==9
archive=ROOT/'archive/camera-before298-2026-10-19';manifest=load(archive/'manifest.json')
assert manifest['prior_documented_stage']==297 and len(manifest['files'])==9
for row in manifest['files']:
 p=archive/row['path'];assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256']
deployment=load(ROOT/'linux-port/camera/deployment-lock.json');source=load(ROOT/'linux-port/camera/kernel/source-lock.json')
identity=load(HERE/'postboot-identity-validation.json');health=load(HERE/'final-health-validation.json');package=load(HERE/'boot-package-validation.json');build=load(HERE/'boot-candidate-build-validation.json')
assert all(d['stage']==298 for d in [deployment,source,identity,health,package,build])
assert deployment['kernel_source_commit']==source['maintained_commit']==package['commit']==build['commit']==checkpoint['source']
assert deployment['kernel_release']==source['actual_kernel_release']==identity['release']==health['release']==package['release']==build['release']
assert deployment['kernel_modules']==source['deployed_camera_modules']==health['modules']
for key in ['image_sha256','logdump_sha256','dtb_sha256']:assert deployment[key]==package[key]
assert deployment['boot_sha256']==package['firmware_boot_preserved_sha256']
assert deployment['kernel_config_sha256']==build['artifacts']['.config']['sha256']
assert health['checked_runtime_healthy'] and not health['whole_system_healthy']
assert not health['first_statistics_packet_invalid'] and not health['statistics_ready_for_automatic_exposure']
assert not deployment['ssc_boot_start_failed'] and deployment['system_services']['ssc_running'] and not deployment['system_services']['temporary_nodeps_desktop_start']
sof=load(HERE/'sof-association-validation.json');assert sof['shared_sof_contract_passed'] and sof['all_five_observable_roi_transitions_exact']
assert sof['image_frames']==126 and sof['valid_statistics_packets']==111 and sof['sof_events']==128 and sof['statistics_starvation_sequence_gap']==7
assert load(HERE/'blc-capture-validation.json')['passed'] and load(HERE/'scene-capture-validation.json')['passed']
assert load(HERE/'raw-capture-validation.json')['passed']
assert load(HERE/'four-camera-regression-validation.json')['passed'] and load(HERE/'four-camera-regression-validation.json')['frames']==233
assert load(HERE/'blc-pixel-validation.json')['all_phase_color_contracts_passed']
assert load(HERE/'blc-frame-association-validation.json')['exact_frame_association_proven']
scene=load(HERE/'scene-analysis-validation.json');assert scene['black_only_reduces_brightness'] and scene['provisional_wb_reduces_global_green_excess'] and scene['analogue_gain_increases_brightness']
assert not scene['covered_lens_dark_calibration_completed'] and not scene['hardware_pipeline_ipa_integrated'] and scene['scene_estimates_not_installed_as_tuning']
for tag,source_name,binary in [('blc','samurai-blc.c','blc-aarch64-private'),('scene','samurai-scene.c','scene-aarch64-private'),('raw','samurai-raw.c','physical-raw-aarch64-private')]:
 proof=load(HERE/(tag+'-tool-validation.json'));assert sha(P/binary)==proof['binary_sha256'] and sha(HERE/source_name)==proof['source_sha256']
pins=load(HERE/'blc-protocol-validation.json')
for row in pins['sources']:
 assert sha(P.parent/'kernel297'/(row['url'].rsplit('/',1)[-1]+'-reference-private'))==row['sha256']
assert sha(P.parent/'kernel297/bls_1_2_0.xsd-reference-private')==pins['schema_source']['sha256']
assert sha(P.parent/'kernel296/titan170-ife-source-0-private.h')==pins['generated_header_sha256']
for tag in ['parent','fixed']:
 r=load(HERE/f'blc-{tag}-host-validation.json');assert r['expected_outcome_observed']
 assert sha(P/f'blc-{tag}-host-private.c')==r['harness_sha256']
compiled=0
for p in HERE.glob('*.py'):compile(p.read_bytes(),str(p),'exec');compiled+=1
text=(ROOT/'NEXT-SESSION.md').read_text();assert len(text.encode())<=6500 and '## 当前部署与启动身份' in text and '## 源码回退与下一步' in text
assert (ROOT/'DOCS-INDEX.md').stat().st_size<=10000
tree='/home/cy122/x2pro-linux/camera279-isp-kernel';git=lambda *a:subprocess.check_output(['git','-C',tree,*a],text=True).strip()
assert git('rev-parse','HEAD')==checkpoint['source'] and not git('status','--porcelain')
patch=subprocess.check_output(['git','-C',tree,'diff','ab709d9670f6dcaa71858fd4f3e189522f669913..HEAD'])
assert patch==(HERE/'blc-candidate.patch').read_bytes()
for name in ['camss-vfe-175-pixel.c','camss-vfe-175-pixel.h']:
 assert (HERE/name).read_bytes()==(Path(tree)/'drivers/media/platform/qcom/camss'/name).read_bytes()
assert sha(P/'Image-k298-private')==package['image_sha256'] and sha(P/'logdump-k298-candidate-private.img')==package['logdump_sha256']
for name,row in load(HERE.parent/'kernel297/boot-candidate-build-validation.json')['artifacts'].items():
 p=P/'completed-boot297'/Path(name).name;assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256']
state=load(P/'boot-build-state-private.json');assert state['terminal'] and state['exit_code']==0
for name in ['blc-poll-private.json','scene-poll-private.json','raw-poll-private.json','four-camera298-poll-private.json','quiesce-poll-private.json']:
 probe=load(P/name);assert probe['state']['terminal'] and probe['state']['exit_code']==0 and not probe['matching_worker_live']
assert not (P/'flash-logdump-private.log').exists() and (P/'flash-logdump-r2-private.log').exists()
assert all(load(P/n)['request_count']==1 for n in ['flash-request-private.json','reboot-request-private.json','fastboot-reboot-request-private.json'])
raw=load(HERE/'raw-analysis-validation.json');assert raw['raw_decoder_matches_native_mean'] and not raw['sensor_dark_calibration_completed']
for row in load(HERE/'raw-transfer-validation.json')['frames']:assert sha(P/f"raw-{row['frame']}-private.raw")==row['sha256']
oem=load(HERE/'oem-tuning-source-validation.json')
assert oem['unmounted'] and oem['readonly_noload_noexec'] and oem['calibration_values_not_accepted']
assert sha(P/'sunny-imx319-tuning-private.bin')==oem['sha256']
assert oem['identified_parameter_roots']['bls12_ife']==16 and oem['user_selected_normal_scene_comparison_without_dark_cover']
for name,digest in oem['source_scripts'].items():assert sha(HERE/name)==digest
report=dict(stage=298,current_source_and_runtime_receipts_consistent=True,source_clean=True,all_nine_archived_entrypoints_verified=True,
 source_and_binary_probe_hashes_verified=True,all_bls_reference_hashes_verified=True,new_python_scripts_compiled=compiled,
 entrypoint_size_and_anchors_passed=True,previous_build_artifacts_verified=True,actual_default_ssc_success_preserved=True,
 all_physical_workers_terminal=True,flash_preflight_failure_preserved_and_single_flash_verified=True,
 black_mapping_and_shared_sof_contracts_passed=True,physical_scene_estimate_improvement_measured=True,
 covered_lens_calibration_pending=True,hardware_pipeline_ipa_incomplete=True,scene_tuning_not_installed=True,
 original_vendor_tuning_source_verified_and_unmounted=True,unvalidated_factory_values_not_installed=True,
 whole_system_healthy=False,complete_goal_still_incomplete=True)
(HERE/'final-checkpoint-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
