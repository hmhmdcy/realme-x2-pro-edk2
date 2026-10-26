from pathlib import Path
import hashlib, json, subprocess

ref = Path(__file__).parent
kernel = Path('/home/cy122/pmos-samurai-kernel136/kernel')
old = json.loads((ref.parent / 'kernel176/source-validation.json').read_text())['source_sha256']
now = {p: hashlib.sha256((kernel / p).read_bytes()).hexdigest() for p in old}
assert now == old, 'Kernel sources changed since build176'
tracked = subprocess.check_output(['git', '-C', str(kernel), 'diff', '--name-only'], text=True).splitlines()
assert len(tracked) == 10
ngd = (kernel / 'drivers/slimbus/qcom-ngd-ctrl.c').read_text()
assert 'SET_SYSTEM_SLEEP_PM_OPS(pm_runtime_force_suspend,' in ngd
assert 'pm_runtime_force_resume)' in ngd
config = (kernel / '.config').read_text()
assert 'CONFIG_SUSPEND=y' in config and '# CONFIG_PM_DEBUG is not set' in config
report = dict(stage=177, deployed_kernel_build=176, kernel_sources_unchanged_from176=True,
              source_sha256=now, tracked_files=tracked, ngd_system_pm_uses_runtime_force_suspend_resume=True,
              config_suspend_enabled=True, config_pm_debug_disabled=True,
              no_new_kernel_build_or_flash=True,
              kernel_pm_documentation='https://docs.kernel.org/admin-guide/pm/sleep-states.html',
              device_pm_documentation='https://docs.kernel.org/driver-api/pm/types.html')
(ref / 'source-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print('SOURCE177_VERIFIED_UNCHANGED_KERNEL176')
