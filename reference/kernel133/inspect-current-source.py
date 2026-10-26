from pathlib import Path
import hashlib
import json
import runpy
import subprocess
r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel133'
out = Path('/mnt/e/edk2-samurai-out/kernel133')
runpy.run_path(str(r / 'reference/kernel118/ensure-build-volume.py'))
k = Path('/home/cy122/pmos-samurai-kernel118/power132/kernel')
files = ['drivers/power/supply/qcom_smbx.c', 'arch/arm64/boot/dts/qcom/pm8150b.dtsi', 'arch/arm64/boot/dts/qcom/sm8150-samurai.dts', 'drivers/power/supply/mp2650_charger.c', 'drivers/usb/typec/tcpm/qcom/qcom_pmic_typec.c', 'drivers/usb/typec/tcpm/qcom/qcom_pmic_typec_port.c']
copies = {}
for name in files:
    p = k / name
    if p.is_file():
        payload = p.read_bytes()
        target = out / ('current132--' + name.replace('/', '--'))
        assert not target.exists()
        target.write_bytes(payload)
        copies[name] = dict(bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest())
config = (k / '.config').read_text()
selected = [l for l in config.splitlines() if any(s in l for s in ['TYPEC', 'QCOM_SMB', 'CHARGER_MP2650', 'USB_ROLE_SWITCH'])]
head = subprocess.check_output(['git', '-C', str(k), 'rev-parse', 'HEAD'], text=True).strip()
stock = json.loads((r / 'reference/kernel76/stock-source-manifest.json').read_text())
for name in ['drivers/power/oppo/charger_ic/oppo_mp2650.c', 'drivers/power/oppo/charger_ic/oppo_mp2650.h']:
    p = out.parent / 'kernel76' / ('stock-' + Path(name).name)
    assert hashlib.sha256(p.read_bytes()).hexdigest() == stock['files'][name]['sha256']
report = dict(stage=133, current_kernel_source_head=head, current132_sources=copies,
              selected_configuration=selected, stock_mp2650_source_and_header_hashes_reverified=True,
              stock_commit=stock['commit'], no_kernel_source_or_phone_changes=True, goal_complete=False)
(ref / 'source-inspection-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report), flush=True)
