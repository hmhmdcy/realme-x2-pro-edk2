from pathlib import Path
import hashlib,json,subprocess
import host
code=b'''from pathlib import Path
import json,subprocess
root=Path('/var/lib/samurai/k190-usb-stall');root.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k189r2-reboot-runtime/boot-id-private.txt').read_bytes()
for cmd,name in [(['dmesg'],'dmesg-private.txt'),(['ip','-j','-s','link'],'links-private.json'),(['ip','-j','address'],'addresses-private.json'),(['ip','-j','-6','neighbor'],'neighbors-private.json')]:
 p=subprocess.run(cmd,capture_output=True,check=True);(root/name).write_bytes(p.stdout)
states={}
for p in Path('/sys/class/udc').glob('*'):
 states[p.name]={name:(p/name).read_text().strip() for name in ['state','current_speed','maximum_speed'] if (p/name).exists()}
for p in Path('/sys/class/net').glob('*'):
 if not p.name.startswith(('usb','rndis')):continue
 states[p.name]={name:(p/name).read_text().strip() for name in ['operstate','carrier','mtu','device/power/runtime_status'] if (p/name).exists()}
report=dict(same_boot=True,states=states,usb_dmesg=[line for line in (root/'dmesg-private.txt').read_text().splitlines() if any(word in line.lower() for word in ['f_ncm','gadget','dwc3','usb0','xhci'])][-35:])
(root/'summary-private.json').write_text(json.dumps(report,indent=2));print(json.dumps(dict(same_boot=True,states=states)))
'''
p=host.ssh('python3 -',input=code);print(p.stdout.decode())
for name in ['summary-private.json','addresses-private.json','links-private.json']:
 host.download('/var/lib/samurai/k190-usb-stall/'+name,host.PRIVATE/name)
record=json.loads((host.PRIVATE/'summary-private.json').read_text())
addresses=json.loads((host.PRIVATE/'addresses-private.json').read_text())
expected=json.loads((host.PRIVATE.parent/'kernel189/reboot-r2/usb-ipv6-candidates-private.json').read_text(encoding='utf-8-sig'))['IPAddress'].split('%')[0]
public=dict(same_boot_as189=True,states=record['states'],phone_has_expected_usb_ipv6=any(a['local']==expected for x in addresses if x['ifname'].startswith(('usb','rndis')) for a in x['addr_info']),usb_new_kernel_errors=sum('error' in line.lower() or 'timeout' in line.lower() for line in record['usb_dmesg']))
(Path(__file__).resolve().parent/'usb-stall-validation.json').write_text(json.dumps(public,indent=2)+'\n');print(json.dumps(public))
