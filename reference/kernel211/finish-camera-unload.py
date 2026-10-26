from pathlib import Path
import json,subprocess
root=Path('/var/lib/samurai');out=root/'k211-quiesce';assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k211-before-reboot/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='512'
assert not Path('/sys/bus/i2c/devices/7-0010/driver').exists() and Path('/sys/module/imx471/refcnt').read_text().strip()=='0'
assert Path('/sys/bus/platform/devices/ac4b000.cci/power/control').read_text().strip()=='auto'
before=subprocess.check_output(['dmesg']);assert before.count(b'WARNING:')==2
report=dict(stage=211,known_mclk_warning_count=2,taint=512,sensor_already_unbound=True,unload_results=[])
for i,name in enumerate(['imx471','qcom_camss','v4l2_cci','qcom_pm8008_regulator','qcom_pm8008','i2c_qcom_cci']):
    p=subprocess.run(['rmmod',name],capture_output=True,timeout=15);(out/('recovery-camera-unload-'+str(i)+'-private.log')).write_bytes(p.stdout+p.stderr);report['unload_results'].append(dict(module=name,exit=p.returncode));assert p.returncode==0
after=subprocess.check_output(['dmesg']);(out/'recovery-camera-dmesg-private.txt').write_bytes(after)
assert after.count(b'WARNING:')==2 and not Path('/dev/media0').exists()
report.update(all_six_camera_modules_unloaded=True,no_additional_warnings=True)
(out/'camera-quiesce-recovery-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
