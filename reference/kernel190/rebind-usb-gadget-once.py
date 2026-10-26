"""Recover the single NCM gadget over authenticated Wi-Fi; do not reboot the phone."""
from pathlib import Path
import hashlib,json,time
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k189r2-reboot-runtime/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
root=Path('/var/lib/samurai/k190-usb-rebind');root.mkdir(mode=0o700)
gadgets=list(Path('/sys/kernel/config/usb_gadget').iterdir());assert len(gadgets)==1
gadget=gadgets[0];assert gadget.name=='samurai'
assert [p.name for p in (gadget/'functions').iterdir()]==['ncm.usb0']
udc=gadget/'UDC';original=udc.read_text().strip();assert original=='a600000.usb'
state=Path('/sys/class/udc')/original/'state';assert state.read_text().strip()=='configured'
report=dict(stage=190,only_function='ncm.usb0',same_boot_as189=True,phone_rebooted=False,unbind_writes=0,bind_writes=0)
try:
 udc.write_text('\n');report['unbind_writes']+=1
 assert udc.read_text().strip()==''
 time.sleep(.5)
finally:
 if udc.read_text().strip()=='':udc.write_text(original+'\n');report['bind_writes']+=1
 report['original_udc_restored']=udc.read_text().strip()==original
 deadline=time.monotonic()+15
 while state.read_text().strip()!='configured' and time.monotonic()<deadline:time.sleep(.1)
 report['final_udc_state']=state.read_text().strip()
 report['same_boot_after']=Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k189r2-reboot-runtime/boot-id-private.txt').read_bytes()
 (root/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
assert report['original_udc_restored'] and report['same_boot_after']
