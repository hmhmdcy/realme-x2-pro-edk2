from pathlib import Path
import hashlib,json,subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel293')
load=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
checkpoint=load(HERE/'checkpoint-validation.json')
for name,row in checkpoint['files'].items():assert (ROOT/name).stat().st_size==row['bytes'] and sha(ROOT/name)==row['sha256']
archive=ROOT/'archive/camera-before292-2026-10-19'
for row in load(archive/'manifest.json')['files']:assert (archive/row['path']).stat().st_size==row['bytes'] and sha(archive/row['path'])==row['sha256']
deployment=load(ROOT/'linux-port/camera/deployment-lock.json');source=load(ROOT/'linux-port/camera/kernel/source-lock.json');identity=load(HERE/'postboot-identity-validation.json');health=load(HERE/'final-health-validation.json');package=load(HERE/'boot-package-validation.json');build=load(HERE/'boot-candidate-build-validation.json')
assert all(d['stage']==293 for d in [deployment,source,identity,health,package,build])
assert deployment['kernel_source_commit']==source['maintained_commit']==package['commit']==build['commit']==checkpoint['source']
assert deployment['kernel_release']==source['actual_kernel_release']==identity['release']==health['release']==package['release']==build['release']
assert deployment['kernel_modules']==source['deployed_camera_modules']==health['modules']
for key in ['image_sha256','logdump_sha256','dtb_sha256']:assert deployment[key]==package[key]
assert deployment['boot_sha256']==package['firmware_boot_preserved_sha256']
assert deployment['kernel_config_sha256']==build['artifacts']['.config']['sha256']
assert deployment['ssc_boot_start_failed'] and not deployment['automatic_rotation_currently_available'] and not health['whole_system_healthy']
assert deployment['system_services']['ssc_running']==False and deployment['system_services']['temporary_nodeps_desktop_start']
assert health['camera_tests_and_resource_health_passed'] and health['ssc_default_start_failed']
for tag in ['wb-params','optical']:
 proof=load(HERE/(tag+'-tool-validation.json'));assert sha(PRIVATE/(tag+'-aarch64-private'))==proof['binary_sha256'] and sha(HERE/('samurai-'+tag+'.c'))==proof['source_sha256']
for folder in ['kernel292','kernel293']:
 for p in (HERE.parent/folder).glob('*.py'):compile(p.read_bytes(),str(p),'exec')
text=(ROOT/'NEXT-SESSION.md').read_text();assert len(text.encode())<=6500 and '## 当前部署与启动身份' in text and '## 源码回退与下一步' in text
tree='/home/cy122/x2pro-linux/camera279-isp-kernel';git=lambda *a:subprocess.check_output(['git','-C',tree,*a],text=True).strip()
assert git('rev-parse','HEAD')==checkpoint['source'] and not git('status','--porcelain')
assert subprocess.check_output(['git','-C',tree,'diff','15c8639d8badf5d4146bfd1b2c2fcb2460a137e5..HEAD','--','drivers/media/platform/qcom/camss'])==(HERE/'combined-params-from290.patch').read_bytes()
report=dict(stage=293,current_source_and_runtime_receipts_consistent=True,source_clean=True,all_nine_archived_entrypoints_verified=True,
 source_and_binary_probe_hashes_verified=True,all_new_python_scripts_compile=True,entrypoint_size_and_anchors_passed=True,
 actual_ssc_failure_and_desktop_recovery_preserved=True,complete_goal_still_active=True)
(HERE/'final-checkpoint-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
