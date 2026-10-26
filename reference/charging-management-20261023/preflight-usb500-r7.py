"""Read-only network prerequisites before the frozen USB500 coordinator."""
from pathlib import Path
import importlib.util
import json

REF=Path(__file__).resolve().parent
OUT=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/usb500-r7-preflight')
CODE=r'''from pathlib import Path
import json,subprocess,time
start=time.clock_gettime(time.CLOCK_BOOTTIME)
links=json.loads(subprocess.check_output(['ip','-j','-6','addr','show','dev','usb0'],timeout=3))
addresses=[a for link in links for a in link.get('addr_info',[])
 if a.get('local')=='fe80::62:bcff:fe28:a101' and a.get('prefixlen')==64 and a.get('scope')=='link']
assert len(addresses)==1 and not set(addresses[0].get('flags',[])).intersection(['tentative','dadfailed'])
assert not any(addresses[0].get(k,False) for k in ['tentative','dadfailed'])
g=Path('/sys/kernel/config/usb_gadget/samurai');s=Path('/sys/class/power_supply/samurai-usb-input')
assert (g/'functions/ncm.usb0/ifname').read_text().strip()=='usb0'
assert (g/'UDC').read_text().strip()=='a600000.usb' and (g/'configs/c.1/MaxPower').read_text().strip()=='100'
assert Path('/sys/class/udc/a600000.usb/state').read_text().strip()=='configured'
assert '[SDP]' in (s/'usb_type').read_text()
assert (s/'current_max').read_text().strip()==(s/'input_current_limit').read_text().strip()=='100000'
print(json.dumps({'passed':True,'read_only':True,'ip_json_ipv6_supported':True,'observed_peer_dad_complete':True,
 'configured_sdp100':True,'duration_seconds':time.clock_gettime(time.CLOCK_BOOTTIME)-start}))
'''

if __name__=='__main__':
    OUT.mkdir(mode=0o700,exist_ok=True)
    spec=importlib.util.spec_from_file_location('window',REF/'device-window.py')
    window=importlib.util.module_from_spec(spec);spec.loader.exec_module(window)
    q=window.host.ssh('python3 -',input=CODE.encode(),timeout=12,check=False)
    (OUT/'stdout-private.json').write_bytes(q.stdout)
    (OUT/'stderr-private.txt').write_bytes(q.stderr)
    if q.returncode:
        print(q.stderr.decode(errors='replace')[-1500:]);raise SystemExit(q.returncode)
    print(q.stdout.decode())
