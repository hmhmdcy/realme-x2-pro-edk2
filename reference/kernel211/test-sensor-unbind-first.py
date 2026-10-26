from pathlib import Path
import json,subprocess
root=Path('/var/lib/samurai');out=root/'k211-remove-order-test'
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k211-before-reboot/boot-id-private.txt').read_bytes()
report=json.loads((out/'summary.json').read_text());assert report['phase']=='remove-sensor-before-camss' and report['commands'][-1]==dict(command='rmmod',module='imx471',exit=1)
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='512'
before=subprocess.check_output(['dmesg']);assert before.count(b'WARNING:')==1
sensor=Path('/sys/bus/i2c/devices/7-0010');assert (sensor/'driver').resolve()==Path('/sys/bus/i2c/drivers/imx471')
assert Path('/sys/bus/platform/devices/acb3000.camss/driver').exists()
assert all(Path(p,'power/runtime_status').read_text().strip()=='suspended' for p in ['/sys/bus/i2c/devices/7-0010','/sys/bus/platform/devices/acb3000.camss','/sys/bus/platform/devices/ac4b000.cci'])
report['sensor_module_refcount_before_unbind']=int(Path('/sys/module/imx471/refcnt').read_text());report['phase']='unbind-sensor-before-camss'
def save():(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
save();Path('/sys/bus/i2c/drivers/imx471/unbind').write_text('7-0010\n');assert not (sensor/'driver').exists()
after=subprocess.check_output(['dmesg']);(out/'sensor-unbind-dmesg-private.txt').write_bytes(after);report['new_warnings']=after.count(b'WARNING:')-before.count(b'WARNING:');report['sensor_module_refcount_after_unbind']=int(Path('/sys/module/imx471/refcnt').read_text());save();assert report['new_warnings']==0
for name in ['imx471','qcom_camss','v4l2_cci','qcom_pm8008_regulator','qcom_pm8008','i2c_qcom_cci']:
    p=subprocess.run(['rmmod',name],capture_output=True,timeout=20);report['commands'].append(dict(command='rmmod',module=name,exit=p.returncode));(out/('command-'+str(len(report['commands']))+'-private.log')).write_bytes(p.stdout+p.stderr)
    log=subprocess.check_output(['dmesg']);(out/('dmesg-'+str(len(report['commands']))+'-private.txt')).write_bytes(log);report['new_warnings']=log.count(b'WARNING:')-before.count(b'WARNING:');save();assert p.returncode==0 and report['new_warnings']==0
assert all(not Path('/sys/module'/Path(n)).exists() for n in ['imx471','qcom_camss','v4l2_cci','qcom_pm8008_regulator','qcom_pm8008','i2c_qcom_cci'])
report.update(phase='complete',sensor_unbind_before_camss_without_new_warning=True,all_six_unloaded=True,final_taint=int(Path('/proc/sys/kernel/tainted').read_text()));save();print(json.dumps(report))
