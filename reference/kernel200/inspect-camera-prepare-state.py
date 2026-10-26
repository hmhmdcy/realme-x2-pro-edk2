from pathlib import Path
import json,subprocess
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k200-runtime/boot-id-private.txt').read_bytes()
p=root/'k200-live-prepare-r1';r=dict(live_prepare_exists=p.exists(),files=[x.name for x in p.iterdir()] if p.exists() else [],modules={n:Path('/sys/module/'+n).exists() for n in ['i2c_qcom_cci','samurai_cci_bringup','samurai_vio_phandle','qcom_pm8008','v4l2_cci','imx471','samurai_front_overlay']},taint=Path('/proc/sys/kernel/tainted').read_text().strip())
if (p/'attempts.json').exists():r['attempts']=json.loads((p/'attempts.json').read_text())
log=subprocess.check_output(['dmesg']);r['warnings']=log.count(b'WARNING:');r['oops']=log.count(b'Oops:')
print(json.dumps(r))
