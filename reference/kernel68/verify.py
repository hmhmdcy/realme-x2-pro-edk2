"""Offline audit of captured bytes and device-verified saved files. No phone access."""
from pathlib import Path
from hashlib import sha256
import base64,gzip,json,re,sys

root=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parent
def read(name):
    p=root/name
    return p.read_bytes() if p.exists() else gzip.decompress((root/(name+'.gz')).read_bytes())
def frames(raw):
    pos=0;out=[]
    while pos<len(raw):
        assert raw[pos]==0x90 and 1<=raw[pos+1]<=4
        end=pos+2+raw[pos+1];assert end<=len(raw)
        out.append(raw[pos:end]);pos=end
    return out
def exported(capture,marker):
    text=read(capture+'.txt').decode('ascii').replace('\r','')
    begin=re.search(rf'(?m)^{marker}B$',text);assert begin,marker
    end=re.search(rf'(?m)^{marker}E$',text[begin.end():]);assert end,marker
    lines=text[begin.end():begin.end()+end.start()].strip().splitlines()
    digest=lines[0].split()[0];assert re.fullmatch('[0-9a-f]{64}',digest)
    data=base64.b64decode(''.join(lines[1:]),validate=True)
    assert sha256(data).hexdigest()==digest
    return data,gzip.decompress(data),digest

result=dict(captures=[],exports=[])
for name in ('baseline','baseline-read','opp','opp-read','opp-f1'):
    raw=read(name+'.raw');fs=frames(raw)
    assert b''.join(f[2:] for f in fs).decode('ascii',errors='replace').encode()==read(name+'.txt')
    meta=json.loads(read(name+'.json'))
    events=[json.loads(s) for s in read(name+'.events.jsonl').decode().splitlines()]
    incoming=[]
    for line in read(name+'.usbmon').decode().splitlines():
        fields=line.split();addr=fields[3].split(':')
        assert tuple(map(int,addr[1:3]))==(meta['bus'],meta['address'])
        if addr[0]=='Bi' and fields[2]=='C' and int(fields[5]):
            b=bytes.fromhex(''.join(fields[7:]));assert len(b)==int(fields[5])
            incoming.append(b)
    assert b''.join(incoming)==raw
    if name=='opp-f1':
        assert meta['frame']=='90 02' and meta['setup'] is None and not meta['explicit_out_zlp']
        assert len([e for e in events if e['event']=='out_submit'])==1
        assert any(e['event']=='receipt' and e['text']=='F1' for e in events)
        assert events[-1]['event']=='read_error'
    else:
        end=events[-1]
        assert end['event']=='closed' and not end['worker_alive'] and not end['errors']
        assert end['sink_drained'] and end['pending']==end['stray']==0
        assert end['io_bytes']==len(raw) and end['frames']==len(fs) and not end['overlap_used']
        assert not meta['automatic_data_retries']
    result['captures'].append(dict(name=name,raw_bytes=len(raw),frames=len(fs),positive_usb_in_equals_raw=True))

windows=json.loads(read('windows-close-observations.json'))['captures']
for name,expected in windows.items():
    raw=read(name+'.raw');fs=frames(raw)
    assert b''.join(f[2:] for f in fs)==read(name+'.txt')
    assert len(fs)==expected['frames']
    events=read(name+'.events.txt').decode()
    if 'native len=' in events:
        for line in events.splitlines():
            if 'TX native' in line and 'sync=False' in line:
                assert 'attempt=1 ' in line
    result['captures'].append(dict(name=name,raw_bytes=len(raw),frames=len(fs),close_observed=True,retries=expected['retries']))

for name,capture,marker in (
    ('baseline-facts','baseline','K68BF'),('baseline-bootmeta','baseline','K68BP'),
    ('opp-dmesg','opp-win-log','K68WL'),('opp-facts','opp-win-facts','K68WF')):
    data,body,digest=exported(capture,marker)
    assert data==read(name+'-received.gz') and body==read(name+'.validated.txt')
    result['exports'].append(dict(name=name,compressed_bytes=len(data),plain_bytes=len(body),sha256=digest,device_sha256_pass=True,gzip_crc_pass=True))
baseline=read('baseline-bootmeta.validated.txt')
assert b'6678528 /tmp/K68B/boot-prefix' in baseline and b'8c9dea12a8eca687f9da59e067da8c3dfb91bec4d61ae3371c67292d434c7edd' in baseline
log=read('opp-dmesg.validated.txt');facts=read('opp-facts.validated.txt')
assert len(log)==52842 and sha256(log).hexdigest()=='072040c4cabc3299c62e900775089627e92ba43c4f414db34b3d2f4544896e6f'
assert not any(s in log for s in (b'Voltage update failed freq=2956800',b'Kernel panic',b'Oops:',b'dwc3: failed to initialize core',b'mm/ioremap.c:23'))
assert log.count(b'Attached SCSI disk')==6
assert facts.startswith(b'afbbf870-b998-43d8-ab3d-42b3c68c0122\n0\n')
assert b'cpuinfo_max_freq:2956800' in facts and b'scaling_max_freq:2956800' in facts
assert b'/opp-table-cpu7/opp-2956800000\na600000.usb\n' in facts
available=re.search(rb'scaling_available_frequencies:([^\n]+)',facts).group(1).split()
assert b'2956800' in available and b'4294967295' not in available
audit=json.loads(read('firmware-validation.json'))
assert audit['sole_semantic_dtb_change']=='/opp-table-cpu7/opp-2956800000'
assert audit['other_executable_bytes_unchanged'] and audit['bootshim_bytes']==144 and audit['fd_bytes']==0x700000
assert audit['boot_after_bytes']==6682624 and audit['boot_after_sha256']=='785071a405d839b13d3d0ef040f42d227b09659e6dd0d3df96bb3689ced0635b'
assert sha256(read('firmware-before.dtb')).hexdigest()=='68001bab92e8611373200f2928d1d83ef5256890528df59dea92c72c1900756e'
assert sha256(read('firmware-after.dtb')).hexdigest()=='4641207124f1276f00749132d118ba73c3fdeaef24aeac8b2b1df017ef5dea9a'
bad=json.loads(read('opp-dmesg-first-failed.json'))
assert not bad['validated'] and bad['no_filling'] and bad['received_bytes']==12371 and bad['device_bytes']==12377
finish=json.loads(read('finish-state.json'));flash=json.loads(read('boot-flash-validation.json'))
assert flash['flash_success'] and flash['reboot_success'] and flash['partition']=='boot'
assert finish['flashed_partitions']==['boot'] and finish['boot_written']
assert not any(finish[k] for k in ('logdump_written','userdata_written','gpt_written'))
assert not finish['known_owners'] and not finish['known_linux_owners']
assert len(finish['nodes'])==3 and all(n['Status']=='OK' for n in finish['nodes'])
assert re.search(r'(?m)^6-5\s+05c6:9505\s+[^\r\n]*Shared\s*$',finish['usbipd'])
assert finish['temporary_logging_absent'] and not finish['active_eud_trace']
result['cpu7']=dict(live_opp_present=True,max_khz=2956800,warnings_removed=True,taint=0,high_frequency_stress_tested=False)
result['finish']=dict(com14_windows=True,known_owners=[],boot_only_flash=True,android_data_preserved=True)
if (root/'manifest.json').exists():
    for name,expected in json.loads(read('manifest.json'))['files'].items():
        b=(root/name).read_bytes();assert len(b)==expected['bytes'] and sha256(b).hexdigest()==expected['sha256'],name
    result['manifest_pass']=True
print(json.dumps(result,indent=2))
