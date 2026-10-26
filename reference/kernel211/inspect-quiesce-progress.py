from pathlib import Path
import json,subprocess
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k211-before-reboot/boot-id-private.txt').read_bytes()
out=root/'k211-quiesce'
report=dict(stage=211,files=sorted(p.name for p in out.iterdir()),camera=json.loads((out/'camera-quiesce-validation.json').read_text()) if (out/'camera-quiesce-validation.json').exists() else None,modules={n:Path('/sys/module'/Path(n)).exists() for n in ['qcom_camss','imx471','v4l2_cci','qcom_pm8008_regulator','qcom_pm8008','i2c_qcom_cci']},remoteprocs={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')},taint=int(Path('/proc/sys/kernel/tainted').read_text()),gui_pids=subprocess.run(['pgrep','-u','10000'],capture_output=True,text=True).stdout.split(),camss_pm=Path('/sys/bus/platform/devices/acb3000.camss/power/runtime_status').read_text().strip())
print(json.dumps(report))
