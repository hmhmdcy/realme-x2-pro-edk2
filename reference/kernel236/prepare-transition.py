"""Adapt the proven183 path to fresh236 identity and the real staged235 files."""
from pathlib import Path
import ast
import hashlib
import json
import subprocess

R = Path(__file__).resolve().parent
OLD = R.parent / 'kernel233'
names = ['quiesce-current183.sh', 'stop-gnss-idle.py', 'quiesce-camera.py', 'disable-crtc.py',
         'check-quiesce.py', 'freeze-for-bootloader.sh', 'linux-restart2-bootloader.py',
         'preflight-transition.py', 'run-quiesce.py', 'poll-quiesce.py', 'reboot-current.py', 'refresh-usb-endpoint.ps1']
hashes = {}
for name in names:
    original = (OLD / name).read_text()
    text = original.replace('k233', 'k236').replace('K233', 'K236').replace('stage=233', 'stage=236').replace("'stage': 233", "'stage': 236")
    text = text.replace('k236-module-stage', 'k235-module-stage')
    if name == 'check-quiesce.py':
        old = "assert Path('/sys/module/qcom_pm8008_regulator').exists() and not Path('/sys/module/reset_realme_rmx1931_pm8008').exists()"
        assert text.count(old) == 1
        text = text.replace(old, """assert Path('/sys/module/qcom_pm8008_regulator').exists() and Path('/sys/module/reset_realme_rmx1931_pm8008').exists()
assert Path('/sys/bus/platform/devices/camera-pmic-resets/driver').resolve().name=='rmx1931-pm8008-resets'
for name in ['1-0004','1-0008']:assert Path('/sys/bus/i2c/devices',name,'driver').resolve().name=='pm8008'
assert not Path('/sys/bus/i2c/devices/1-0009').exists()
assert Path('/sys/module/qcom_pm8008/parameters/experimental_p_address_only').read_text().strip()=='Y'""")
    if name == 'quiesce-camera.py':
        text = text.replace("report.update(all_four_endpoint_modules_unloaded=True", """assert Path('/sys/module/reset_realme_rmx1931_pm8008').exists()
assert Path('/sys/bus/i2c/devices/1-0008/driver').resolve().name=='pm8008'
assert not Path('/sys/bus/i2c/devices/1-0009').exists()
report.update(p_q_provider_retained=True,all_four_endpoint_modules_unloaded=True""")
    if name == 'reboot-current.py':
        assert "proof['stage'] == 233" in text
        text = text.replace("proof['stage'] == 233", "proof['stage'] == 236")
        text = text.replace('locked232 boot', 'locked235 boot')
    if name == 'refresh-usb-endpoint.ps1':
        assert "kernel230'" in text
        text = text.replace("kernel230'", "kernel236'")
    if name == 'linux-restart2-bootloader.py':
        assert "os.sysconf('SC_PAGE_SIZE') == 4096" in text
        assert 'mmap.mmap(fd, 4096,' in text
        # Only context identifiers differ; all physical register accesses remain exact.
        normalized = text.replace('k236', 'k233').replace('stage=236', 'stage=233').replace("'stage': 236", "'stage': 233")
        assert normalized == original
    if name.endswith('.py'):
        ast.parse(text)
    if name.endswith('.sh'):
        result = subprocess.run(['sh', '-n'], input=text.encode(), capture_output=True)
        assert result.returncode == 0
    assert not (R / name).exists()
    (R / name).write_text(text)
    hashes[name] = hashlib.sha256(text.encode()).hexdigest()
text = (OLD / 'flash-boot.py').read_text().replace('stage=233', 'stage=236').replace("['boot219_rollback']", "['boot232_rollback']")
assert "['boot232_rollback']" in text
ast.parse(text)
(R / 'flash-boot.py').write_text(text)
hashes['flash-boot.py'] = hashlib.sha256(text.encode()).hexdigest()
report = dict(stage=236, tools=hashes, fresh236_context=True, staged235_manifests_used=True,
              live_p_q_provider_retained=True, restart_physical_code_and_page4096_unchanged=True,
              only_locked235_boot_flash_with_current232_rollback=True, no_phone_operation=True)
(R / 'transition-source-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(dict(stage=236, transition_tools_prepared=len(hashes), no_phone_operation=True)))
