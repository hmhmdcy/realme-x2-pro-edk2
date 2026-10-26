"""Read-only probes of previously recorded handset leases using the original host key."""
from pathlib import Path
import importlib.util, ipaddress, json, re, subprocess
import host
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('strict303wifi', HERE.parent/'kernel190/host.py')
transport = importlib.util.module_from_spec(spec); spec.loader.exec_module(transport)
base = transport.transport.parent.transport.base_transport()
addresses = []
for path in sorted((host.PRIVATE.parent/'kernel98').rglob('dhcp-lease.txt'), key=lambda p:p.stat().st_mtime, reverse=True):
    match = re.search(r'^ip=(\d+\.\d+\.\d+\.\d+)$', path.read_text(), re.M)
    if match:
        address = match[1]; assert ipaddress.ip_address(address).is_private
        if address not in addresses: addresses.append(address)
assert len(addresses) <= 3
native = b"from pathlib import Path\nimport json,os\nprint(json.dumps(dict(same_298_guard=Path('/var/lib/samurai/k298-work/boot-id-private.txt').read_bytes()==Path('/proc/sys/kernel/random/boot_id').read_bytes(),expected_model=Path('/sys/firmware/devicetree/base/model').read_bytes()==b'Realme X2 Pro (RMX1931CN)\\0',release=os.uname().release,build=os.uname().version,taint=int(Path('/proc/sys/kernel/tainted').read_text()),uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]))))\n"
records = []
for index, address in enumerate(addresses):
    try:
        q = subprocess.run([base.SSH, '-T', *base.OPTIONS, '-4', '-o', 'HostKeyAlias=169.254.42.1', 'root@'+address,
                            'python3 -'], input=native, capture_output=True, timeout=15)
        (host.PRIVATE/f'wifi-probe-{index}-private.log').write_bytes(q.stdout+q.stderr)
        record = dict(candidate_index=index, exit=q.returncode, responsive=q.returncode==0)
        if q.returncode == 0:
            proof = json.loads(q.stdout); assert proof['expected_model']
            record.update(proof)
            (host.PRIVATE/'fresh-working-endpoint-private.json').write_text(json.dumps(dict(kind='wifi',IPAddress=address,proof=proof),indent=2)+'\n')
    except subprocess.TimeoutExpired as error:
        (host.PRIVATE/f'wifi-probe-{index}-private.log').write_bytes((error.stdout or b'')+(error.stderr or b''))
        record = dict(candidate_index=index,responsive=False,timed_out=True)
    records.append(record)
    if record['responsive']: break
report = dict(stage=303,strict_original_host_key=True,no_device_mutation=True,probes=records,
              working_endpoint_found=any(r['responsive'] for r in records))
(HERE/'wifi-probe-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
