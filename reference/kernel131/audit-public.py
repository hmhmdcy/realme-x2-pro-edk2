from pathlib import Path
import json

root = Path('/mnt/e/RealmeX2Pro edk2')
source = (root / 'reference/kernel130/audit-public.py').read_text()
source = source.replace('129,130]:', '129,130,131]:')
source = source.replace('range(109,131)', 'range(109,132)')
source = source.replace("r/'reference/kernel130/public-audit.json'", "r/'reference/kernel131/public-audit.json'")
exec(compile(source, 'prior-audit-expanded-to-131', 'exec'))
path = root / 'reference/kernel131/public-audit.json'
report = json.loads(path.read_text())
hardware = (root / 'linux-port/docs/HARDWARE-STATUS.md').read_text()
assert '阶段131' in hardware and 'GPU整体失败' in hardware
report.update(stage=131, single_fixed_fbo_scene_pixel_pass=True,
              gpu_translation_faults_this_boot=2, gpu_overall_acceptance=False,
              standard_mp2650_nonempty_events=8, charging_control_accepted=False,
              rootfs_generation=130, goal_complete=False)
path.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
