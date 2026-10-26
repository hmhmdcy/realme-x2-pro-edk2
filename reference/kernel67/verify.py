"""Offline evidence audit. No device access, retries, or reconstruction of lost text."""
from pathlib import Path
from hashlib import sha256
import base64, gzip, json, re, sys

root=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parent
def read(name):
    path=root/name
    return path.read_bytes() if path.exists() else gzip.decompress((root/(name+'.gz')).read_bytes())
def exported(capture,marker):
    text=read(capture+'.txt').decode('ascii').replace('\r','')
    begin=re.search(rf'(?m)^{marker}B$',text)
    assert begin,marker
    end=re.search(rf'(?m)^{marker}E$',text[begin.end():])
    assert end,marker
    lines=text[begin.end():begin.end()+end.start()].strip().splitlines()
    digest=lines[0].split()[0]
    data=base64.b64decode(''.join(lines[1:]),validate=True)
    assert sha256(data).hexdigest()==digest,marker
    return data,gzip.decompress(data),digest

result={'captures':[],'verified_exports':[]}
for name in ('before','opp','usb','usb-read','opp-f1','usb-f1'):
    raw=read(name+'.raw')
    pos=0
    frames=[]
    while pos<len(raw):
        assert raw[pos]==0x90 and 1<=raw[pos+1]<=4
        end=pos+2+raw[pos+1]
        assert end<=len(raw)
        frames.append(raw[pos:end]);pos=end
    assert b''.join(f[2:] for f in frames).decode('ascii',errors='replace').encode()==read(name+'.txt')
    meta=json.loads(read(name+'.json'))
    events=[json.loads(line) for line in read(name+'.events.jsonl').decode().splitlines()]
    incoming=[]
    for line in read(name+'.usbmon').decode().splitlines():
        fields=line.split();addr=fields[3].split(':')
        assert tuple(map(int,addr[1:3]))==(meta['bus'],meta['address'])
        if addr[0]=='Bi' and fields[2]=='C' and int(fields[5]):
            block=bytes.fromhex(''.join(fields[7:]))
            assert fields[6]=='=' and len(block)==int(fields[5])
            incoming.append(block)
    assert b''.join(incoming)==raw,name
    if name.endswith('-f1'):
        assert meta['frame']=='90 02' and meta['setup'] is None and not meta['explicit_out_zlp']
        submissions=[e for e in events if e['event']=='out_submit']
        assert len(submissions)==1 and submissions[0]['hex']=='90 02'
        assert any(e['event']=='receipt' and e['text']=='F1' for e in events)
        assert events[-1]['event']=='read_error'  # Reboot disconnect after the fresh receipt.
    else:
        assert b''.join(bytes.fromhex(e['hex']) for e in events if e['event']=='in')==raw
        closed=events[-1]
        assert closed['event']=='closed' and not closed['worker_alive'] and not closed['errors']
        assert closed['sink_drained'] and closed['stray']==closed['pending']==0
        assert closed['io_bytes']==len(raw) and closed['frames']==len(frames)
        assert not closed['overlap_used'] and not meta['automatic_data_retries']
    result['captures'].append(dict(name=name,raw_bytes=len(raw),frames=len(frames),sha256=sha256(raw).hexdigest(),positive_usb_in_equals_raw=True,receipt_timeouts=sum(e['event']=='receipt_timeout' for e in events),no_overlap_or_data_retries=True))

for name,capture,marker in (
    ('opp-facts','opp','K67OF'),('opp-dmesg','opp','K67OR'),('opp-live-dt','opp','K67OL'),
    ('usb-facts','usb-read','K67UF'),('usb-dmesg','usb-read','K67UR'),
):
    data,body,digest=exported(capture,marker)
    assert read(name+'-received.gz')==data and read(name+'.validated.txt')==body
    result['verified_exports'].append(dict(name=name,bytes=len(data),plain_bytes=len(body),device_sha256=digest,sha256_pass=True,gzip_crc_pass=True))
opp=read('opp-dmesg.validated.txt')
assert len(opp)==52982 and sha256(opp).hexdigest()=='7c72b69f83170e06789106996541f79b02e341f5f81f159e3750453b4ad27d61'
assert opp.count(b'Voltage update failed freq=2956800')==2
assert read('opp-live-dt.validated.txt').startswith(b'OPP_ABSENT\n')
opp_facts=read('opp-facts.validated.txt')
assert b'83952af2-74ee-4dad-9e01-16ee951d4c20\n0\n' in opp_facts
assert b'CONFIG_PHY_QCOM_USB_SNPS_FEMTO_V2=m' in opp_facts
usb=read('usb-dmesg.validated.txt')
assert len(usb)==53788 and sha256(usb).hexdigest()=='1a42e5406e88458205f01e8acdec3593508e9b8e31a039c1659a047f6caa874a'
facts=read('usb-facts.validated.txt')
assert b'CONFIG_PHY_QCOM_USB_SNPS_FEMTO_V2=y' in facts
assert b'#60 ' in facts and b'28e3bd68-2dd4-46f5-a24b-95f237ec070b\n0\nlrwx' in facts
assert b'qcom-snps-hs-femto-v2-phy' in facts and b'/drivers/dwc3' in facts
assert b'a600000.usb ->' in facts and b'dwc3: failed to initialize core' not in usb
assert b'generic_ioremap_prot' not in usb and b'mm/ioremap.c:23' not in usb
assert usb.count(b'Attached SCSI disk')==6
assert b'Kernel panic' not in usb and b'Oops:' not in usb
before=read('config-usb-before');after=read('config-usb-after')
assert after==before.replace(b'CONFIG_PHY_QCOM_USB_SNPS_FEMTO_V2=m\n',b'CONFIG_PHY_QCOM_USB_SNPS_FEMTO_V2=y\n')
audit=json.loads(read('usb-source-audit.json'))
assert audit['initramfs_kernel_modules']==0 and audit['built_in_manifest_entry']
assert not audit['fat_dtb_override_in_current_load_options']
result['cpu7_opp_candidate']=dict(compiled=True,fat_copy_flashed=True,live_node_present=False,runtime_fixed=False,firmware_dtb_still_used=True)
result['usb_step']=dict(config_change_only=True,hs_phy_bound=b'qcom-snps-hs-femto-v2-phy' in facts,dwc3_bound=b'/drivers/dwc3' in facts,core_failure_in_snapshot=b'dwc3: failed to initialize core' in usb,udc_present=b'a600000.usb ->' in facts,no_panic_in_this_snapshot=True)
bad=json.loads(read('opp-dmesg-first-failed.json'))
assert not bad['validated'] and bad['no_filling'] and bad['base64_chars']<bad['expected_base64_chars']
finish=json.loads(read('finish-state.json'))
assert not finish['known_owners'] and not finish['known_linux_owners']
assert all(n['Status']=='OK' for n in finish['nodes']) and len(finish['nodes'])==3
assert re.search(r'(?m)^6-5\s+05c6:9505\s+[^\r\n]*Shared\s*$',finish['usbipd'])
assert finish['flashed_partitions']==['logdump','logdump']
assert not any(finish[k] for k in ('boot_written','userdata_written','gpt_written'))
assert finish['temporary_logging_absent'] and not finish['active_eud_trace']
result['finish']=dict(com14_windows=True,unattached=True,known_owners=[],original_files_verified=True,logdump_only_flashes=2)
if (root/'manifest.json').exists():
    manifest=json.loads(read('manifest.json'))
    for name,want in manifest['files'].items():
        data=(root/name).read_bytes()
        assert len(data)==want['bytes'] and sha256(data).hexdigest()==want['sha256'],name
    result['manifest_pass']=True
print(json.dumps(result,indent=2))
