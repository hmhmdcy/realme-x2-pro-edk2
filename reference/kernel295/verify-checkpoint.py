"""Verify actual source/artifacts/checkpoints while retaining incomplete statistics status."""
from pathlib import Path
import hashlib,json,subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];P=Path('/mnt/e/edk2-samurai-out/kernel295')
load=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
checkpoint=load(HERE/'checkpoint-validation.json')
for name,row in checkpoint['files'].items():assert (ROOT/name).stat().st_size==row['bytes'] and sha(ROOT/name)==row['sha256']
archive=ROOT/'archive/camera-before294-2026-10-19'
for row in load(archive/'manifest.json')['files']:assert (archive/row['path']).stat().st_size==row['bytes'] and sha(archive/row['path'])==row['sha256']
deployment=load(ROOT/'linux-port/camera/deployment-lock.json');source=load(ROOT/'linux-port/camera/kernel/source-lock.json');identity=load(HERE/'postboot-identity-validation.json');health=load(HERE/'final-health-validation.json');package=load(HERE/'boot-package-validation.json');build=load(HERE/'boot-candidate-build-validation.json')
assert all(d['stage']==295 for d in [deployment,source,identity,health,package,build])
assert deployment['kernel_source_commit']==source['maintained_commit']==package['commit']==build['commit']==checkpoint['source']
assert deployment['kernel_release']==source['actual_kernel_release']==identity['release']==health['release']==package['release']==build['release']
assert deployment['kernel_modules']==source['deployed_camera_modules']==health['modules']
for key in ['image_sha256','logdump_sha256','dtb_sha256']:assert deployment[key]==package[key]
assert deployment['boot_sha256']==package['firmware_boot_preserved_sha256']
assert deployment['kernel_config_sha256']==build['artifacts']['.config']['sha256']
assert not deployment['ssc_boot_start_failed'] and deployment['automatic_rotation_currently_available'] and not health['whole_system_healthy']
assert deployment['system_services']['ssc_running'] and not deployment['system_services']['temporary_nodeps_desktop_start']
assert health['checked_runtime_healthy'] and health['first_statistics_packet_invalid']
assert not load(HERE/'statistics-pixel-validation.json')['passed'] and not deployment['statistics_ready_for_automatic_exposure']
assert load(HERE/'statistics-pixel-validation.json')['steady_roi_contracts_passed'] and load(HERE/'optical-statistics-validation.json')['stable_exposure_response_and_return_passed']
for tag in ['stats','optical']:
 proof=load(HERE/(tag+'-tool-validation.json'));assert sha(P/(tag+'-aarch64-private'))==proof['binary_sha256'] and sha(HERE/('samurai-'+tag+'.c'))==proof['source_sha256']
compiled=0
for folder in ['kernel294','kernel295']:
 for p in (HERE.parent/folder).glob('*.py'):compile(p.read_bytes(),str(p),'exec');compiled+=1
text=(ROOT/'NEXT-SESSION.md').read_text();assert len(text.encode())<=6500 and '## 当前部署与启动身份' in text and '## 源码回退与下一步' in text
assert (ROOT/'DOCS-INDEX.md').stat().st_size<=10000
tree='/home/cy122/x2pro-linux/camera279-isp-kernel';git=lambda *a:subprocess.check_output(['git','-C',tree,*a],text=True).strip()
assert git('rev-parse','HEAD')==checkpoint['source'] and not git('status','--porcelain')
patch=subprocess.check_output(['git','-C',tree,'diff','1aa1955077c977b611c722eca0bc467c3bf052ed..HEAD','--','drivers/media/platform/qcom/camss'])
assert patch==(HERE/'combined-stats-from293.patch').read_bytes()
assert sha(P/'Image-k295-private')==package['image_sha256'] and sha(P/'logdump-k295-candidate-private.img')==package['logdump_sha256']
for stage in [294,295]:
 q=load(P.parent/f'kernel{stage}/boot-build-r2-state-private.json') if stage==294 else load(P/'boot-build-state-private.json')
 assert q['terminal'] and q['exit_code']==0
report=dict(stage=295,current_source_and_runtime_receipts_consistent=True,source_clean=True,all_nine_archived_entrypoints_verified=True,
 source_and_binary_probe_hashes_verified=True,new_python_scripts_compiled=compiled,entrypoint_size_and_anchors_passed=True,
 actual_default_ssc_success_preserved=True,prior_ssc_failure_not_claimed_fixed=True,
 first_statistics_packet_failure_preserved=True,statistics_not_ready_for_ipa=True,complete_goal_still_active=True)
(HERE/'final-checkpoint-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
