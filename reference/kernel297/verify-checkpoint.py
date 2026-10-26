"""Verify deployed artifacts, finished probes, preserved failures and current docs."""
from pathlib import Path
import hashlib,json,subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];P=Path('/mnt/e/edk2-samurai-out/kernel297')
load=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
checkpoint=load(HERE/'checkpoint-validation.json')
for name,row in checkpoint['files'].items():
 p=ROOT/name;assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],name
archive=ROOT/'archive/camera-before297-2026-10-19';manifest=load(archive/'manifest.json')
assert manifest['prior_documented_stage']==296 and len(manifest['files'])==9
for row in manifest['files']:
 p=archive/row['path'];assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256']
deployment=load(ROOT/'linux-port/camera/deployment-lock.json');source=load(ROOT/'linux-port/camera/kernel/source-lock.json')
identity=load(HERE/'postboot-identity-validation.json');health=load(HERE/'final-health-validation.json');package=load(HERE/'boot-package-validation.json');build=load(HERE/'boot-candidate-build-validation.json')
assert all(d['stage']==297 for d in [deployment,source,identity,health,package,build])
assert deployment['kernel_source_commit']==source['maintained_commit']==package['commit']==build['commit']==checkpoint['source']
assert deployment['kernel_release']==source['actual_kernel_release']==identity['release']==health['release']==package['release']==build['release']
assert deployment['kernel_modules']==source['deployed_camera_modules']==health['modules']
for key in ['image_sha256','logdump_sha256','dtb_sha256']:assert deployment[key]==package[key]
assert deployment['boot_sha256']==package['firmware_boot_preserved_sha256']
assert deployment['kernel_config_sha256']==build['artifacts']['.config']['sha256']
assert health['checked_runtime_healthy'] and not health['whole_system_healthy']
assert not health['first_statistics_packet_invalid'] and not health['statistics_ready_for_automatic_exposure']
assert not deployment['ssc_boot_start_failed'] and deployment['system_services']['ssc_running'] and not deployment['system_services']['temporary_nodeps_desktop_start']
sof=load(HERE/'sof-association-validation.json')
assert sof['shared_sof_contract_passed'] and sof['all_five_observable_roi_transitions_exact']
assert sof['image_frames']==126 and sof['valid_statistics_packets']==111 and sof['sof_events']==128
assert sof['statistics_starvation_sequence_gap']==7 and not sof['statistics_error_packets']
assert not load(HERE/'stats-capture-validation.json')['passed'] and load(HERE/'stats-r2-capture-validation.json')['passed']
assert load(HERE/'optical-statistics-validation.json')['all_packets_valid']
assert load(HERE/'four-camera-regression-validation.json')['passed'] and load(HERE/'four-camera-regression-validation.json')['frames']==232
assert load(HERE/'stats-pixel-validation.json')['all_phase_color_contracts_passed']
assert load(HERE/'frame-association-validation.json')['exact_frame_association_proven']
for tag in ['stats','stats-r2','optical']:
 proof=load(HERE/(tag+'-tool-validation.json'))
 assert sha(P/(tag+'-aarch64-private'))==proof['binary_sha256'] and sha(HERE/('samurai-'+tag+'.c'))==proof['source_sha256']
for row in load(HERE/'blc-protocol-validation.json')['sources']:
 assert sha(P/(row['url'].rsplit('/',1)[-1]+'-reference-private'))==row['sha256']
compiled=0
for p in HERE.glob('*.py'):compile(p.read_bytes(),str(p),'exec');compiled+=1
text=(ROOT/'NEXT-SESSION.md').read_text();assert len(text.encode())<=6500 and '## 当前部署与启动身份' in text and '## 源码回退与下一步' in text
assert (ROOT/'DOCS-INDEX.md').stat().st_size<=10000
tree='/home/cy122/x2pro-linux/camera279-isp-kernel';git=lambda *a:subprocess.check_output(['git','-C',tree,*a],text=True).strip()
assert git('rev-parse','HEAD')==checkpoint['source'] and not git('status','--porcelain')
patch=subprocess.check_output(['git','-C',tree,'diff','f86906688666c0ebaabaeeec96c28d5741257f50..HEAD'])
assert patch==(HERE/'sof-candidate.patch').read_bytes()
assert sha(P/'Image-k297-private')==package['image_sha256'] and sha(P/'logdump-k297-candidate-private.img')==package['logdump_sha256']
for name,row in load(HERE.parent/'kernel296/boot-candidate-build-validation.json')['artifacts'].items():
 p=P/'completed-boot296'/Path(name).name;assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256']
state=load(P/'boot-build-state-private.json');assert state['terminal'] and state['exit_code']==0
for name,expected in [('stats-poll-private.json',1),('stats-r2-poll-private.json',0),('optical-poll-private.json',0),('four-camera295-poll-private.json',0)]:
 probe=load(P/name);assert probe['state']['terminal'] and probe['state']['exit_code']==expected and not probe['matching_worker_live']
report=dict(stage=297,current_source_and_runtime_receipts_consistent=True,source_clean=True,all_nine_archived_entrypoints_verified=True,
 source_and_binary_probe_hashes_verified=True,all_four_bls_reference_hashes_verified=True,new_python_scripts_compiled=compiled,
 entrypoint_size_and_anchors_passed=True,previous_build_artifacts_verified=True,actual_default_ssc_success_preserved=True,
 all_physical_workers_terminal=True,failed_r1_preserved=True,r2_shared_sof_and_roi_contracts_passed=True,statistics_not_ready_for_ipa=True,
 black_level_and_full_iq_incomplete=True,whole_system_healthy=False,complete_goal_still_incomplete=True)
(HERE/'final-checkpoint-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
