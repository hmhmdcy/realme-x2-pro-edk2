"""Isolate the sensor MCLK dependency with the controller's normal PM API."""
from pathlib import Path
import json,signal,subprocess,time
root=Path('/var/lib/samurai');out=root/'k211-cci-power-hold';out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k211-before-reboot/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='512'
before=subprocess.check_output(['dmesg']);assert before.count(b'WARNING:')==2
sensor=Path('/sys/bus/i2c/devices/7-0010');assert not (sensor/'driver').exists()
assert Path('/sys/module/imx471').exists() and Path('/sys/bus/platform/devices/acb3000.camss/driver').exists()
cci=Path('/sys/bus/platform/devices/ac4b000.cci');control=cci/'power/control';original=control.read_text().strip();assert original=='auto'
report=dict(stage=211,known_warning_count_before=2,original_cci_control=original,events=[],control_restored=False)
def save():(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
def record(label):
    log=subprocess.check_output(['dmesg']);(out/(label+'-dmesg-private.txt')).write_bytes(log)
    (out/(label+'-genpd-private.txt')).write_bytes(Path('/sys/kernel/debug/pm_genpd/pm_genpd_summary').read_bytes())
    report['events'].append(dict(label=label,cci=(cci/'power/runtime_status').read_text().strip(),sensor_bound=(sensor/'driver').exists(),warnings_delta=log.count(b'WARNING:')-before.count(b'WARNING:')));save();assert report['events'][-1]['warnings_delta']==0
def interrupt(signum,frame):raise RuntimeError('Interrupted CCI PM observation; restore original policy')
for sig in [signal.SIGTERM,signal.SIGINT,signal.SIGHUP]:signal.signal(sig,interrupt)
save()
try:
    control.write_text('on\n');assert (cci/'power/runtime_status').read_text().strip()=='active';record('cci-held-active')
    Path('/sys/bus/i2c/drivers/imx471/bind').write_text('7-0010\n');assert (sensor/'driver').exists();time.sleep(.2);record('sensor-bound')
    Path('/sys/bus/i2c/drivers/imx471/unbind').write_text('7-0010\n');assert not (sensor/'driver').exists();record('sensor-unbound-with-controller-active')
    report['sensor_probe_and_remove_without_new_clock_warning']=True
finally:
    if (sensor/'driver').exists():Path('/sys/bus/i2c/drivers/imx471/unbind').write_text('7-0010\n')
    control.write_text(original+'\n');time.sleep(.2);report['control_restored']=control.read_text().strip()==original;save()
assert report['control_restored']
print(json.dumps(report))
