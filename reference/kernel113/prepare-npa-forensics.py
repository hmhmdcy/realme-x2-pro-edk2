from pathlib import Path
import hashlib,json,struct,subprocess,tarfile,urllib.request

out=Path('/mnt/e/edk2-samurai-out/kernel113')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
repo=out/'npa-code-reference-private'
revision='b5e5bb9ed6c92442fd502b3e726d7c8024dc0763'
assert subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD']).decode().strip()==revision
reference=out/'npa-api-source-private';reference.mkdir(exist_ok=True)
paths=['cdsp_proc/core/api/power/npa.h','cdsp_proc/core/api/systemdrivers/icbarb.h',
    'cdsp_proc/core/api/systemdrivers/icbid.h','cdsp_proc/core/power/npa/src/framework/npa_client.c',
    'cdsp_proc/core/systemdrivers/icb/src/common/ul_arb.c',
    'cdsp_proc/core/systemdrivers/icb/src/common/ul_int.c','cdsp_proc/core/api/power/npa_resource.h']
references=[]
for name in paths:
    blob=subprocess.check_output(['git','-C',str(repo),'rev-parse',revision+':'+name],timeout=10).decode().strip()
    path=reference/Path(name).name
    if path.exists(): payload=path.read_bytes()
    else:
        with (reference/(path.name+'.fetch-private.log')).open('wb') as errors:
            attempt=subprocess.run(['git','-C',str(repo),'-c','http.version=HTTP/1.1','show',revision+':'+name],
                stdout=subprocess.PIPE,stderr=errors,timeout=40)
        if attempt.returncode==0: payload=attempt.stdout
        else:
            url='https://raw.githubusercontent.com/David112x/android-firmware-qti-sdm660/'+revision+'/'+name
            with urllib.request.urlopen(url,timeout=20) as response: payload=response.read(256*1024+1)
            assert len(payload)<=256*1024
        path.write_bytes(payload)
    assert hashlib.sha1(b'blob '+str(len(payload)).encode()+bytes([0])+payload).hexdigest()==blob
    references.append(dict(path=name,git_blob=blob,sha256=hashlib.sha256(payload).hexdigest(),bytes=len(payload)))
(ref/'npa-api-reference.json').write_text(json.dumps(dict(
    repository='https://github.com/David112x/android-firmware-qti-sdm660',revision=revision,
    origin='Qualcomm API/source mirrored in an SDM660 reference; not device firmware',files=references,
    source_executed=False,sm8150_abi_not_yet_proven=True,phone_changed=False),indent=2)+'\n')
print(json.dumps(dict(api_reference_files=len(references),git_blobs_verified=True)),flush=True)

source=Path('/mnt/e/edk2-samurai-out/kernel111/source-files/k111-sensor-sources-readonly/firmware')
with tarfile.open(out/'sensor-ram-v17.tar') as archive:
    manifest=archive.extractfile('./original-firmware.sha256').read().decode()
expected={Path(name).name:digest for digest,name in (line.split('  ',1) for line in manifest.splitlines())}
assert expected
for name,digest in expected.items():
    assert hashlib.sha256((source/name).read_bytes()).hexdigest()==digest
mdt=(source/'slpi.mdt').read_bytes()
assert mdt[:6]==b'\x7fELF\x01\x01' and struct.unpack_from('<H',mdt,18)[0]==164
offset=struct.unpack_from('<I',mdt,28)[0]
step,count=struct.unpack_from('<HH',mdt,42)
assert step==32 and offset+step*count<=len(mdt)
segments=[];maximum=len(mdt)
for index in range(count):
    kind,fileoff,va,pa,filesz,memsz,flags,alignment=struct.unpack_from('<IIIIIIII',mdt,offset+step*index)
    if filesz:
        payload=(source/f'slpi.b{index:02d}').read_bytes()
        assert len(payload)==filesz
        maximum=max(maximum,fileoff+filesz)
    if kind==1 and filesz and (flags>>24)&7!=2:
        segments.append(dict(index=index,fileoff=fileoff,va=va,pa=pa,filesz=filesz,memsz=memsz,flags=flags))
assert maximum<32*1024*1024
image=bytearray(maximum);image[:len(mdt)]=mdt
for index in range(count):
    kind,fileoff,va,pa,filesz,memsz,flags,alignment=struct.unpack_from('<IIIIIIII',mdt,offset+step*index)
    if filesz: image[fileoff:fileoff+filesz]=(source/f'slpi.b{index:02d}').read_bytes()
assert image[:6]==mdt[:6]
# Descriptive section headers are host analysis metadata. This ELF is never
# deployed: original split files/MDT remain untouched and keep their signatures.
names=bytearray(bytes([0]));sections=[bytes(40)]
for segment in segments:
    name=(('.text' if segment['flags']&1 else '.data')+str(segment['index'])).encode()+bytes([0])
    nameoff=len(names);names.extend(name)
    sections.append(struct.pack('<IIIIIIIIII',nameoff,1,2|(4 if segment['flags']&1 else 0)|(1 if segment['flags']&2 else 0),
        segment['va'],segment['fileoff'],segment['filesz'],0,0,4,0))
stringname=len(names);names.extend(b'.shstrtab'+bytes([0]))
image.extend(bytes((-len(image))%4));stringoff=len(image);image.extend(names)
sections.append(struct.pack('<IIIIIIIIII',stringname,3,0,0,stringoff,len(names),0,0,1,0))
image.extend(bytes((-len(image))%4));sectionoff=len(image)
image.extend(b''.join(sections))
struct.pack_into('<I',image,32,sectionoff)
struct.pack_into('<HHH',image,46,40,len(sections),len(sections)-1)
analysis=out/'original-slpi-analysis-private.elf'
if analysis.exists(): assert analysis.read_bytes()==image
else: analysis.write_bytes(image)
(out/'original-slpi-analysis-segments-private.json').write_text(json.dumps(segments,indent=2)+'\n')
report=dict(original_firmware_files_verified=len(expected),elf_machine='Hexagon',
    analysis_elf_bytes=len(image),analysis_elf_sha256=hashlib.sha256(image).hexdigest(),
    descriptive_sections_added_for_host_objdump=True,original_program_segments=len(segments),
    executable_sections=sum(bool(x['flags']&1) for x in segments),
    firmware_source_unchanged=True,analysis_elf_not_deployable=True,phone_changed=False)
(ref/'npa-forensic-elf-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
# Disassembly is a separate bounded operation. Preserve the initial partial
# listing; only disassemble independently verified scopes with its own helper.
print('ORIGINAL_FIRMWARE_ANALYSIS_ELF_PREPARED_NOT_DEPLOYABLE',flush=True)
