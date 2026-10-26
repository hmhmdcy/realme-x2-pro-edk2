from pathlib import Path
import json,re,subprocess
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k211-before-reboot/boot-id-private.txt').read_bytes()
out=root/'k211-remove-order-test';report=json.loads((out/'summary.json').read_text())
report['current_modules']={n:Path('/sys/module'/Path(n)).exists() for n in ['qcom_camss','imx471','v4l2_cci','qcom_pm8008_regulator','qcom_pm8008','i2c_qcom_cci']}
report['sensor_bound']=Path('/sys/bus/i2c/devices/7-0010/driver').exists()
log=subprocess.check_output(['dmesg'],text=True);report['clock_warnings']=[l for l in log.splitlines() if 'WARNING:' in l or "cam_cc_mclk2_clk status" in l]
print(json.dumps(report))
