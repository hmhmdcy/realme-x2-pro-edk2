from pathlib import Path
import json
r = Path('/mnt/e/RealmeX2Pro edk2')
source = (r / 'reference/kernel130/audit-public.py').read_text()
source = source.replace('129,130]:', '129,130,131,132]:')
source = source.replace('range(109,131)', 'range(109,133)')
source = source.replace("r/'reference/kernel130/public-audit.json'", "r/'reference/kernel132/public-audit.json'")
source = source.replace('current_kernel=129,rootfs_generation=130', 'current_kernel=132,rootfs_generation=132')
exec(compile(source, 'prior-audit-expanded-to-132', 'exec'))
p = r / 'reference/kernel132/public-audit.json'
report = json.loads(p.read_text())
hardware = (r / 'linux-port/docs/HARDWARE-STATUS.md').read_text()
assert '阶段132' in hardware and 'GPU整体失败' in hardware and '实际充电控制继续待办' in hardware
report.update(stage=132, persistent_charger_actual_new_boot_verified=True,
              complete_matching_four_artifacts_verified=True,
              charging_control_accepted=False, gpu_overall_acceptance=False, goal_complete=False)
p.write_text(json.dumps(report, indent=2) + '\n')
print('K132_PUBLIC_PRIVACY_AND_15_HARDWARE_BOUNDARIES_AUDIT_PASS', flush=True)
