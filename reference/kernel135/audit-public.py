from pathlib import Path
import json
r = Path('/mnt/e/RealmeX2Pro edk2')
source = (r / 'reference/kernel130/audit-public.py').read_text()
source = source.replace('129,130]:', '129,130,131,132,133,134,135]:')
source = source.replace('range(109,131)', 'range(109,136)')
source = source.replace("r/'reference/kernel130/public-audit.json'", "r/'reference/kernel135/public-audit.json'")
source = source.replace('current_kernel=129,rootfs_generation=130', 'current_kernel=132,rootfs_generation=132')
exec(compile(source, 'privacy-audit-expanded-to-135', 'exec'))
p = r / 'reference/kernel135/public-audit.json'
report = json.loads(p.read_text())
hardware = (r / 'linux-port/docs/HARDWARE-STATUS.md').read_text()
assert '阶段135' in hardware and '回退#132' in hardware and 'GPU整体失败' in hardware
assert '当前132无该驱动' in hardware and 'CRTC inactive' in hardware
assert '0x2719为电量计扩展标识' in hardware and '实际充电控制继续待办' in hardware
load = lambda name: json.loads((r / 'reference/kernel135' / name).read_text())
assert load('complete-bundle-validation.json')['candidate_rejected']
assert load('stable-rollback-bundle-validation.json')['matching_stable_four_artifact_hashes_fresh_verified']
assert load('rollback-health-validation.json')['fault_increments_zero']
assert load('host-volume-validation.json')['all_four_private_volumes_unmounted_and_offline_readonly_fsck_zero']
report.update(stage=135, candidate_rejected=True, actual_rollback_kernel=132,
              latest_candidate_rootfs_generation=134, current_usb_input134_driver_present=False,
              automatic_desktop_processes_recovered=True, permanent_display_fix=False,
              gpu_overall_acceptance=False, charging_control_accepted=False,
              physical_camera_accepted=False, complete_matching_four_artifacts_verified=True,
              goal_complete=False)
p.write_text(json.dumps(report, indent=2) + '\n')
print('K135_PUBLIC_PRIVACY_15_GROUP_SCOPE_FAILED_CANDIDATE_AND_CURRENT132_AUDIT_PASS', flush=True)
