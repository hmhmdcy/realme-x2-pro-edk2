from pathlib import Path
import json,os,subprocess

root=Path('/var/lib/samurai');out=root/'k200-quiesce'
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k200-baseline/boot-id-private.txt').read_bytes()
r=dict(files={p.name:p.stat().st_size for p in out.iterdir()},
    remoteprocs={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')},
    user10000_present=subprocess.run(['pgrep','-u','10000'],stdout=subprocess.DEVNULL).returncode==0,
    camss_loaded=Path('/sys/module/qcom_camss').exists(),
    wifi_bound=Path('/sys/bus/platform/devices/18800000.wifi/driver').exists(),
    taint=Path('/proc/sys/kernel/tainted').read_text().strip())
for name in ['samurai-ssc','iio-sensor-proxy','ModemManager','networkmanager','elogind']:
    p=subprocess.run(['rc-service',name,'status'],capture_output=True);r[name+'_running']=p.returncode==0
log=subprocess.check_output(['dmesg']);r['warnings']=log.count(b'WARNING:');r['oops']=log.count(b'Oops:')
print(json.dumps(r))
