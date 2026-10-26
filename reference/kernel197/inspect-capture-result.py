from pathlib import Path
import json,re,subprocess
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k197-baseline/boot-id-private.txt').read_bytes();out=root/'k197-front-capture-r2';report=json.loads((out/'summary.json').read_text()) if (out/'summary.json').exists() else {}
for p in sorted(out.glob('command-*-private.log')):print(p.name,p.read_text()[-2000:])
for name in ['capture-private.log','deferred-private.txt']:
 p=out/name
 if p.exists():print(name,re.sub(r'hash=[0-9a-f]+','hash=<private>',p.read_text())[-3000:])
print(json.dumps({k:report.get(k) for k in ['attempts','resources_applied','normal_driver_bound','physical_media_graph_present','capture_returncode','camss_original_graph_restored','pins_restored_exact','fault_delta','taint']}))
print('loaded', [p.name for p in Path('/sys/module').iterdir() if any(x in p.name for x in ['imx471','pm8008','samurai_','v4l2_cci','i2c_qcom_cci'])]);print('camss_bound',(Path('/sys/bus/platform/devices/acb3000.camss')/'driver').exists());print('current_taint',Path('/proc/sys/kernel/tainted').read_text().strip());log=subprocess.check_output(['dmesg']);before=(out/'dmesg-before-private.txt').read_bytes();delta=log[len(before):] if log.startswith(before) else log[-16000:];(out/'dmesg-current-private.txt').write_bytes(log);print(delta.decode(errors='replace')[-14000:])
