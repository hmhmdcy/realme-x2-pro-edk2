from pathlib import Path
import gzip
import hashlib
import json
import re

root=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
exports=[]
for name in ('baseline-dmesg','usb-dmesg','boot62-dmesg','finish-dmesg','finish-facts'):
    m=json.loads((root/(name+'-validation.json')).read_text())
    filename=m.get('compressed_file',name+'-received.gz')
    data=(root/filename).read_bytes()
    assert sha(data)==m['device_sha256'],name
    body=gzip.decompress(data)
    assert len(body)==m['plain_bytes'] and body==(root/(name+'.validated.txt')).read_bytes(),name
    exports.append(dict(name=name,plain_bytes=len(body),gzip_bytes=len(data),sha256_pass=True))
captures=[]
for p in sorted(root.glob('*.raw')):
    data=p.read_bytes(); pos=0; body=bytearray(); count=0
    while pos<len(data):
        assert data[pos]==0x90 and pos+2<=len(data),(p.name,pos)
        n=data[pos+1]
        assert 1<=n<=4 and pos+2+n<=len(data),(p.name,pos,n)
        body.extend(data[pos+2:pos+2+n]); pos+=2+n; count+=1
    text=(root/(p.stem+'.txt')).read_bytes().decode('utf8')
    decoded=body.decode('utf8',errors='replace')
    if p.stem=='boot-passive': decoded=body.decode('ascii',errors='replace').replace('\ufffd','?')
    assert decoded==text,p.name
    events=root/(p.stem+'.events.txt')
    if events.exists():
        for line in events.read_text().splitlines():
            if 'TX native' in line and 'sync=False' in line:
                assert 'attempt=1' in line and 'len=2 ' not in line,line
    if p.stem.endswith('-wsl'):
        events=[json.loads(x) for x in (root/(p.stem+'.events.jsonl')).read_text().splitlines()]
        assert any(x.get('event')=='receipt' and x.get('text')=='F1' for x in events)
        meta=json.loads((root/(p.stem+'.json')).read_text())
        assert meta['repeat_limit']==1 and meta['read_size']==16 and not meta['explicit_out_zlp'] and meta['setup'] is None
    captures.append(dict(name=p.stem,frames=count,raw_bytes=len(data),decoded_matches=True))
log=(root/'finish-dmesg.validated.txt').read_text()
assert log.startswith('[    0.000000]') and '#62 SMP' in log
assert 'S3706A, fw id: 3078696' in log and log.count('Attached SCSI disk')==6
assert '[usb] CDC NCM usb0/169.254.42.1 with public-key SSH started' in log
assert not re.search(r'Kernel panic - not syncing|Oops:|WARNING:|BUG:',log)
facts=(root/'finish-facts.validated.txt').read_text()
assert '5ecfab9e-fa56-4ead-acf8-a5147904980e\n0\n' in facts
assert 'configured\nhigh-speed\na600000.usb\n' in facts
assert '\n1785600\n2419200\n2956800\n' in facts
assert facts.endswith('0\n0\nK72END\n')
ind=json.loads((root/'independent-ssh-validation.json').read_text())
assert ind['authenticated_ssh_success'] and ind['known_host_key_reused'] and not ind['host_com_up_before_test']
assert 'K72INDEPENDENT\n' in (root/'independent-ssh-ready-facts.txt').read_text()
fl=json.loads((root/'flash-validation.json').read_text())
assert fl['flashed_partitions']==['logdump'] and fl['flash_success'] and fl['reboot_success']
assert not fl['boot_written'] and not fl['userdata_written'] and not fl['gpt_written']
state=json.loads((root/'finish-state.json').read_text())
assert state['host_owner_released'] and state['autonomous_usb_ssh_verified']
assert state['original_driver_inf']=='oem102.inf' and state['original_driver_version']=='2.1.3.5'
assert json.loads((root/'finish-owners.json').read_text())==[]
nodes=json.loads((root/'finish-pnp.json').read_text())
assert len(nodes)==5 and all(n['Status']=='OK' for n in nodes)
usb=(root/'finish-usbipd.txt').read_text()
assert re.search(r'(?m)^6-5\s+05c6:9505\s+[^\r\n]*Shared\s*$',usb)
traffic=json.loads((root/'traffic-validation.json').read_text())
assert len(traffic)==4 and all(x['bytes']==4194304 and x['device_sha256']==x['host_sha256'] and x['sha256_pass'] for x in traffic)
cpio=json.loads((root/'initramfs-validation.json').read_text())
assert cpio['root_ownership_mapping_pass'] and cpio['command_symlinks_pass'] and cpio['private_client_key_absent']
before=(root/'config-before').read_text().splitlines(); after=(root/'config-ncm').read_text().splitlines()
ignore=lambda s:s.startswith(('CONFIG_INITRAMFS_ROOT_UID=','CONFIG_INITRAMFS_ROOT_GID='))
assert [x for x in before if not ignore(x)]==[x for x in after if not ignore(x)]
hook=b'\n# SAMURAI_USB_NCM_SSH: independent of the EUD console and F1 path.\n/usr/sbin/samurai-usb start &\n'
assert (root/'init-after').read_bytes().replace(hook,b'')==(root/'init-before').read_bytes()
assert len((root/'core-preservation.txt').read_text().splitlines())==5
assert all(x.endswith(': OK') for x in (root/'core-preservation.txt').read_text().splitlines())
for p in root.iterdir():
    if p.is_file(): assert not re.search(rb'(?m)^-----BEGIN [A-Z ]*PRIVATE KEY-----$',p.read_bytes()),p.name
if (root/'SHA256SUMS').exists():
    entries={}
    for line in (root/'SHA256SUMS').read_text().splitlines():
        h,n=line.split('  ',1); assert sha((root/n).read_bytes())==h,n; entries[n]=h
    assert set(entries)=={p.name for p in root.iterdir() if p.is_file() and p.name not in ('SHA256SUMS','verification-report.json')}
report=dict(exports=exports,captures=captures,traffic=traffic,autonomous_usb_ssh_pass=True,
            native_eud_retained=True,only_logdump_flashed=True,whole_hardware_goal_complete=False)
(root/'verification-report.json').write_text(json.dumps(report,indent=2)+'\n')
print(f'Verified {len(exports)} saved exports, {len(captures)} raw captures, 4 traffic directions, autonomous SSH, minimal init/config and released owners.')
