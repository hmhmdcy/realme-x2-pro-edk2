from pathlib import Path
import json
import host
records=json.loads((host.PRIVATE/'usb-host-addresses-current-private.json').read_text(encoding='utf-8-sig'))
addresses=[r['IPAddress'].split('%')[0] for r in records if int(r['AddressFamily'])==23 and r['IPAddress'].startswith('fe80:')]
assert len(addresses)==1
code='''from pathlib import Path
import json,subprocess
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k189r2-reboot-runtime/boot-id-private.txt').read_bytes()
root=Path('/var/lib/samurai/k190-usb-stall')
result=subprocess.run(['ping','-6','-I','usb0','-c','2','-W','1',TARGET],capture_output=True,timeout=6)
(root/'phone-to-host-ping-private.log').write_bytes(result.stdout+result.stderr)
gadgets=[]
for p in Path('/sys/kernel/config/usb_gadget').glob('*'):
 gadgets.append(dict(name=p.name,udc=(p/'UDC').read_text().strip(),functions=[x.name for x in (p/'functions').iterdir()],configurations=[x.name for x in (p/'configs').iterdir()]))
report=dict(phone_to_host_ipv6_ping_exit=result.returncode,gadgets=gadgets)
(root/'phone-ping-summary.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
'''.replace('TARGET',repr(addresses[0]))
p=host.ssh('python3 -',input=code.encode(),timeout=15);print(p.stdout.decode())
(Path(__file__).resolve().parent/'usb-phone-ping-validation.json').write_text(json.dumps(json.loads(p.stdout),indent=2)+'\n')
