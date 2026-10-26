from pathlib import Path
import json
import host
code=r'''
from pathlib import Path
import json,subprocess
root=Path('/var/lib/samurai');out=root/'k233-runtime'
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(out/'boot-id-private.txt').read_bytes()
qname=json.loads((root/'k233-baseline/pmic-q-before-private.json').read_text())['device'];pname=qname.rsplit('-',1)[0]+'-0008'
nodes={'q':Path('/sys/bus/i2c/devices')/qname,'p':Path('/sys/bus/i2c/devices')/pname,'provider':Path('/sys/bus/platform/devices/camera-pmic-resets')}
bound={n:bool((p/'driver').is_symlink()) for n,p in nodes.items()}
log=subprocess.check_output(['dmesg'],text=True);(out/'inspect-dmesg-private.txt').write_text(log)
pmic=[l for l in log.splitlines() if 'pm8008' in l.lower() or 'pmic identity' in l.lower() or 'pmic-resets' in l.lower()]
(out/'inspect-pmic-private.txt').write_text('\n'.join(pmic)+'\n')
deferred=Path('/sys/kernel/debug/devices_deferred');deferred_text=deferred.read_text() if deferred.exists() else ''
(out/'inspect-deferred-private.txt').write_text(deferred_text)
ssc=Path('/run/samurai-ssc/state.json');ssc=json.loads(ssc.read_text()) if ssc.exists() else {}
option=Path('/sys/module/qcom_pm8008/parameters/experimental_p_address_only')
report=dict(stage=233,uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]),bound=bound,option=option.read_text().strip() if option.exists() else None,
 taint=int(Path('/proc/sys/kernel/tainted').read_text()),pmic_log_lines=pmic,deferred_device_lines=len(deferred_text.splitlines()),ssc_started=bool(ssc.get('started')),
 fault_counts={n:log.count(s) for n,s in dict(warning='WARNING:',oops='Oops:',gpu='gpu fault:',slpi_fatal='fatal error received',bluetooth='Frame reassembly failed').items()})
(out/'inspect-summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
r=host.ssh('python3 -',input=code.encode(),timeout=20);(host.PRIVATE/'inspect-newboot-host-private.log').write_bytes(r.stdout+r.stderr)
print(r.stdout.decode().strip())
