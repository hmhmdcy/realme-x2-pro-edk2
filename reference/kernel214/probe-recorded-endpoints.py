from pathlib import Path
import importlib.util,ipaddress,json,re,subprocess
here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel214')
spec=importlib.util.spec_from_file_location('strict214',here.parent/'kernel190/host.py');transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport);base=transport.transport.parent.transport.base_transport()
discovery=json.loads((private/'fresh-usb-peers-private.json').read_text(encoding='utf-8-sig'));peers=discovery['Peers'];assert len(peers)<=3
candidates=[]
for peer in peers:
    address=peer['IPAddress'];assert re.fullmatch(r'fe80:[a-fA-F0-9:]+%[0-9]+',address);candidates.append(('usb',address))
addresses=[]
for path in sorted(Path('/mnt/e/edk2-samurai-out/kernel98').rglob('dhcp-lease.txt'),key=lambda p:p.stat().st_mtime,reverse=True):
    match=re.search(r'^ip=(\d+\.\d+\.\d+\.\d+)$',path.read_text(),re.M)
    if match:
        address=match[1];assert ipaddress.ip_address(address).is_private
        if address not in addresses:addresses.append(address)
assert len(addresses)<=3;candidates.extend(('wifi',address) for address in addresses)
native=b"from pathlib import Path\nimport json,os\nroot=Path('/var/lib/samurai');print(json.dumps(dict(same_213_guard=(root/'k213-baseline/boot-id-private.txt').read_bytes()==Path('/proc/sys/kernel/random/boot_id').read_bytes(),expected_model=Path('/sys/firmware/devicetree/base/model').read_bytes()==b'Realme X2 Pro (RMX1931CN)\\0',kernel_build_183=os.uname().version.startswith('#183 '),taint=int(Path('/proc/sys/kernel/tainted').read_text()),uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]))))\n"
records=[]
for index,(kind,address) in enumerate(candidates):
    try:
        p=subprocess.run([base.SSH,'-T',*base.OPTIONS,'-6' if kind=='usb' else '-4','-o','HostKeyAlias=169.254.42.1','root@'+address,'python3 -'],input=native,capture_output=True,timeout=18)
        (private/('endpoint-'+str(index)+'-probe-private.log')).write_bytes(p.stdout+p.stderr)
        record=dict(candidate_index=index,kind=kind,exit=p.returncode,responsive=p.returncode==0)
        if p.returncode==0:
            record.update(json.loads(p.stdout));assert record['expected_model']
            (private/'fresh-working-endpoint-private.json').write_text(json.dumps(dict(kind=kind,IPAddress=address,proof=record),indent=2)+'\n')
    except subprocess.TimeoutExpired as error:
        (private/('endpoint-'+str(index)+'-timeout-private.log')).write_bytes((error.stdout or b'')+(error.stderr or b''));record=dict(candidate_index=index,kind=kind,responsive=False,timed_out=True)
    records.append(record)
    if record['responsive']:break
report=dict(stage=214,fresh_usb_discovery_and_recorded_handset_dhcp_candidates_only=True,strict_original_host_key=True,no_device_mutation=True,probes=records,working_endpoint_found=any(r['responsive'] for r in records))
(here/'fresh-endpoint-probe-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
