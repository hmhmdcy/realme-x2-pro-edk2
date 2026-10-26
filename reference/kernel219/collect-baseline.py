from pathlib import Path
import host,json,shutil

here=Path(__file__).resolve().parent;private=host.PRIVATE
assert not private.exists();private.mkdir(mode=0o700)
shutil.copyfile(private.parent/'kernel218/usb-ipv6-candidates-private.json',private/'usb-ipv6-candidates-private.json')
code=r'''
from pathlib import Path
import hashlib,json,os,shutil,subprocess
os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k219-baseline'
assert not out.exists()
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k218-baseline/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#183 ') and Path('/sys/firmware/devicetree/base/model').read_bytes()==b'Realme X2 Pro (RMX1931CN)\0'
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
module=Path('/usr/lib/modules')/os.uname().release/'kernel/drivers/media/i2c/imx471.ko'
assert hashlib.sha256(module.read_bytes()).hexdigest()=='1388a070e9c902e6b23b3896ce1f50f8f0e44f68d5243ed73e897dcaee186a5b'
assert all(Path(p,'power/runtime_status').read_text().strip()=='suspended' for p in ['/sys/bus/i2c/devices/7-0010','/sys/bus/platform/devices/acb3000.camss','/sys/bus/platform/devices/ac4b000.cci'])
assert Path('/lib/apk/db/installed').read_bytes()==(root/'k218-baseline/installed-before-private.txt').read_bytes()
out.mkdir(mode=0o700)
for source,target in [(Path('/proc/sys/kernel/random/boot_id'),'boot-id-private.txt'),(module,'imx471-original.ko'),(Path('/lib/apk/db/installed'),'installed-before-private.txt')]:shutil.copyfile(source,out/target)
log=subprocess.check_output(['dmesg']);(out/'dmesg-before-private.txt').write_bytes(log)
faults={k:log.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()};assert not any(faults.values())
report=dict(stage=219,fresh_same218_boot_verified=True,module216_and_r5_database_verified=True,camera_suspended=True,taint=0,fault_counts=faults,uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]))
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=45)
(private/'baseline-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);(here/'baseline-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
