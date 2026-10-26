from pathlib import Path
import hashlib,host,json,shutil
here=Path(__file__).resolve().parent;private=host.PRIVATE;private.mkdir(mode=0o700)
shutil.copyfile(private.parent/'kernel216/usb-ipv6-candidates-private.json',private/'usb-ipv6-candidates-private.json')
code=r'''
from pathlib import Path
import hashlib,json,os,shutil,subprocess
os.umask(0o077);root=Path('/var/lib/samurai');base=root/'k217-baseline';assert not base.exists()
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes();assert boot==(root/'k216-baseline/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0' and os.uname().version.startswith('#183 ')
assert Path('/sys/firmware/devicetree/base/model').read_bytes()==b'Realme X2 Pro (RMX1931CN)\0'
assert all(Path(p,'power/runtime_status').read_text().strip()=='suspended' for p in ['/sys/bus/i2c/devices/7-0010','/sys/bus/platform/devices/acb3000.camss','/sys/bus/platform/devices/ac4b000.cci'])
assert json.loads((root/'k216-driver-test-r2/transition-state-private.json').read_text())['state']=='verified'
module=Path('/usr/lib/modules')/os.uname().release/'kernel/drivers/media/i2c/imx471.ko';assert hashlib.sha256(module.read_bytes()).hexdigest()=='1388a070e9c902e6b23b3896ce1f50f8f0e44f68d5243ed73e897dcaee186a5b'
base.mkdir(mode=0o700);(base/'boot-id-private.txt').write_bytes(boot);shutil.copyfile(module,base/'imx471-original.ko')
db=Path('/lib/apk/db/installed').read_bytes();assert db==(root/'k216-baseline/installed-before-private.txt').read_bytes();(base/'installed-before-private.txt').write_bytes(db)
rp={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')};assert len(rp)==3 and all(value=='running' for value in rp.values())
report=dict(stage=217,fresh_same216_boot_verified=True,current_r5_database_unchanged=True,original216_sensor_module_backed_up=True,camera_suspended=True,remoteprocs=rp,taint=0,no_product_change_sent=True)
(base/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=45);(private/'baseline-host-private.log').write_bytes(p.stdout+p.stderr);result=json.loads(p.stdout);(here/'baseline-validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
kernel=Path('/home/cy122/pmos-samurai-kernel136/kernel');path=kernel/'drivers/media/i2c/imx471.c';assert hashlib.sha256(path.read_bytes()).hexdigest()=='cc7562794d1a9b69a0bf7e98f7ed8fcb9e9917b7a6a5c46b833f649a8c60b175';shutil.copyfile(path,private/'imx471-before.c')
lines=path.read_text().splitlines();chosen=set()
for i,line in enumerate(lines):
    if any(word in line for word in ['link_freq','FREQ','clk_set_rate','ext_clk','fwnode','supported_modes','supported_modes','supported_modes','struct imx471_mode']):chosen.update(range(max(0,i-2),min(len(lines),i+8)))
(private/'driver-mode-code-context-private.json').write_text(json.dumps({str(i+1):lines[i] for i in sorted(chosen)},indent=2)+'\n')
