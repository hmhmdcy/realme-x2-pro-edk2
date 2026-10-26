from pathlib import Path, PurePosixPath
import hashlib, json, re, struct, tarfile
import xml.etree.ElementTree as ET

out=Path('/mnt/e/edk2-samurai-out/kernel101')
files={}
with tarfile.open(out/'audio-preflight.tar') as handle:
    for member in handle:
        if not member.isfile():continue
        parts=PurePosixPath(member.name).parts
        assert parts[0]=='k101-audio-preflight' and '..' not in parts
        name=str(PurePosixPath(*parts[1:]));assert name not in files
        files[name]=handle.extractfile(member).read()
checked=set()
for line in files['SHA256SUMS'].decode().splitlines():
    digest,name=line.split('  ',1);name=name.removeprefix('./')
    assert name not in checked and hashlib.sha256(files[name]).hexdigest()==digest
    checked.add(name)
assert checked==files.keys()-{'SHA256SUMS'}
assert files['result.txt']==b'READ_ONLY_AUDIO_PREFLIGHT_PASS\n'
state=files['state.txt'].decode().splitlines()
assert '#99 SMP PREEMPT' in state[0] and state[3:]==['0','running']
assert files['haptics-status.txt'].decode().startswith('id=97 go=00 state=00 ')
assert b'wpa_state=COMPLETED\n' in files['wpa-status.txt'] and b'freq=5180\n' in files['wpa-status.txt']
mounts=files['mounts-during.txt'].decode().splitlines()
assert any('/vendor-mount ext4 ro,' in line and 'norecovery' in line for line in mounts)
assert any('/modem-mount vfat ro,' in line for line in mounts)
assert '/vendor-mount ' not in files['mounts-after.txt'].decode() and '/modem-mount ' not in files['mounts-after.txt'].decode()
assert len(files['nv-check.txt'].decode().splitlines())==6 and all(line.endswith(': OK') for line in files['nv-check.txt'].decode().splitlines())
firmware={name.split('/',1)[1]:data for name,data in files.items() if name.startswith('adsp/')}
assert 'adsp.mdt' in firmware
mdt=firmware['adsp.mdt']
assert mdt[:7]==b'\x7fELF\x01\x01\x01'
assert struct.unpack_from('<H',mdt,18)[0]==164
phoff=struct.unpack_from('<I',mdt,28)[0]
phsize,phnum=struct.unpack_from('<HH',mdt,42)
assert phsize==32 and phoff+phsize*phnum<=len(mdt)
loads=[]
for i in range(phnum):
    typ,offset,vaddr,paddr,filesz,memsz,flags,align=struct.unpack_from('<8I',mdt,phoff+i*phsize)
    if typ!=1 or not memsz or flags&0x7000000==0x2000000:continue
    if filesz:
        segment=f'adsp.b{i:02d}'
        assert segment in firmware and len(firmware[segment])==filesz,(i,filesz)
    loads.append(dict(index=i,paddr=paddr,file_bytes=filesz,memory_bytes=memsz,relocatable=bool(flags&0x8000000)))
minimum=min(p['paddr'] for p in loads)
end=max(p['paddr']+p['memory_bytes'] for p in loads)
size=(end-minimum+4095)&~4095
assert all(p['relocatable'] for p in loads) and size<=0x1e00000
target=out/'adsp-firmware'
assert not target.exists();target.mkdir()
for name,data in firmware.items():
    assert re.fullmatch(r'adsp(?:\.mdt|\.b\d\d|[a-z]*\.jsn)',name),name
    (target/name).write_bytes(data)
controls={}
for name,data in files.items():
    if name.startswith('vendor-config/') and name.endswith('.xml'):
        tree=ET.fromstring(data)
        found=sorted({element.attrib.get('name','') for element in tree.iter('ctl') if re.search(r'max989|tfa|wcd|wsa|speaker|spk',element.attrib.get('name',''),re.I)})
        controls[name]=found
build=files.get('vendor-config/build.prop',b'').decode(errors='replace')
props={key:value for key,value in re.findall(r'^(ro\.(?:product\.first_api_level|board\.first_api_level|build\.version\.(?:sdk|release)))=(.*)$',build,re.M)}
report=dict(readonly_preflight_audit_pass=True,logical_stage=101,kernel_before_build=99,
    verified_private_files=len(checked),archive_sha256=hashlib.sha256((out/'audio-preflight.tar').read_bytes()).hexdigest(),
    firmware_same_handset_installed_modem=True,vendor_readonly_noload=True,mounts_released=True,nv_unchanged=True,
    adsp_firmware_files=len(firmware),adsp_firmware_bytes=sum(len(data) for data in firmware.values()),
    adsp_elf_machine=164,all_load_segments_relocatable=True,adsp_span_bytes=size,
    existing_adsp_carveout_base='0x9b200000',existing_adsp_carveout_bytes=0x1e00000,
    audio_control_names=controls,installed_vendor_properties=props,adsp_started=False,alsa_output_tested=False,
    physical_vibration_confirmed=False,goal_complete=False)
(out/'preflight-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
