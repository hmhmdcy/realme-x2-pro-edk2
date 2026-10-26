from pathlib import Path
import json
r = Path('/mnt/e/RealmeX2Pro edk2')
source = (r / 'reference/kernel130/audit-public.py').read_text()
source = source.replace('129,130]:', '129,130,131,132,133,134]:')
source = source.replace('range(109,131)', 'range(109,135)')
source = source.replace("r/'reference/kernel130/public-audit.json'", "r/'reference/kernel134/public-audit.json'")
source = source.replace('current_kernel=129,rootfs_generation=130', 'current_kernel=134,rootfs_generation=134')
exec(compile(source, 'privacy-audit-expanded-to-134', 'exec'))
p = r / 'reference/kernel134/public-audit.json'
report = json.loads(p.read_text())
hardware = (r / 'linux-port/docs/HARDWARE-STATUS.md').read_text()
assert '阶段134' in hardware and '首次自动启动未验收' in hardware and 'GPU整体失败' in hardware
assert '0x2719为电量计扩展标识' in hardware and '实际充电控制继续待办' in hardware
assert json.loads((r / 'reference/kernel134/complete-bundle-validation.json').read_text())['automatic_full_desktop_startup_accepted'] is False
report.update(stage=134, usb_input_auto_registration_actual_new_boot_verified=True,
              initial_display_boot_failed=True, single_native_panel_reprobe_required=True,
              permanent_display_fix=False, gpu_overall_acceptance=False,
              charging_control_accepted=False, complete_matching_four_artifacts_verified=True, goal_complete=False)
p.write_text(json.dumps(report, indent=2) + '\n')
print('K134_PUBLIC_PRIVACY_15_GROUP_SCOPE_AND_INITIAL_DISPLAY_FAILURE_AUDIT_PASS', flush=True)
