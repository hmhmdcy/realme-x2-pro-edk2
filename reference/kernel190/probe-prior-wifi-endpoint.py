"""Read-only strict-key probes of this handset's previously recorded DHCP addresses."""
from pathlib import Path
import ipaddress,json,re,subprocess
import host
base=host.transport.parent.transport.base_transport()
addresses=[]
for path in sorted(Path('/mnt/e/edk2-samurai-out/kernel98').rglob('dhcp-lease.txt'),key=lambda p:p.stat().st_mtime,reverse=True):
 match=re.search(r'^ip=(\d+\.\d+\.\d+\.\d+)$',path.read_text(),re.M)
 if match:
  addr=match[1];assert ipaddress.ip_address(addr).is_private
  if addr not in addresses:addresses.append(addr)
assert 0<len(addresses)<=3
code=b'''from pathlib import Path
import json,subprocess
old=Path('/var/lib/samurai/k189r2-reboot-runtime/boot-id-private.txt')
report=dict(same_boot_as189=old.exists() and old.read_bytes()==Path('/proc/sys/kernel/random/boot_id').read_bytes(),kernel_build=Path('/proc/version').read_text().split('#')[1].split()[0],uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]),taint=int(Path('/proc/sys/kernel/tainted').read_text()))
print(json.dumps(report))
'''
records=[]
for index,address in enumerate(addresses):
 result=subprocess.run([base.SSH,'-T',*base.OPTIONS,'-4','-o','HostKeyAlias=169.254.42.1','root@'+address,'python3 -'],input=code,capture_output=True,timeout=15)
 (host.PRIVATE/('wifi-readonly-probe-'+str(index)+'-private.log')).write_bytes(result.stdout+result.stderr)
 record=dict(candidate_index=index,exit_code=result.returncode)
 if result.returncode==0:
  record.update(json.loads(result.stdout));(host.PRIVATE/'wifi-current-endpoint-private.json').write_text(json.dumps(dict(IPAddress=address)))
  records.append(record);break
 records.append(record)
(Path(__file__).resolve().parent/'wifi-transport-probe-validation.json').write_text(json.dumps(dict(prior_handset_addresses_only=True,strict_original_host_key=True,read_only=True,probes=records),indent=2)+'\n')
print(json.dumps(records))
