from pathlib import Path
import hashlib,json,re,struct,subprocess,sys,zipfile
variant=sys.argv[1] if len(sys.argv)>1 else 'c28'
assert variant in ('c28','c35','a11')
out=Path('/mnt/e/edk2-samurai-out/kernel113')/(variant+'-reference-private')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
original=Path('/mnt/e/edk2-samurai-out/kernel111/source-files/k111-sensor-sources-readonly/firmware')
if variant=='a11':
    download=json.loads((ref/'a11-package-range-validation.json').read_text())
    assert download['version']=='RMX1931_11.A.11' and download['selected_entry_zip_crc_verified']
    image=out/'modem.img'
    assert image.stat().st_size==download['modem_bytes']
    assert hashlib.sha256(image.read_bytes()).hexdigest()==download['modem_sha256']
else:
    asset={'c28':'Chinese_C28_firmware_only.zip','c35':'Global_C35_firmware_only.zip'}[variant]
    archive=out/asset
    download=json.loads((ref/(variant+'-reference-download.json')).read_text())
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==download['package_sha256']
    image=out/'modem-reference.img'
    if not image.exists():
        with zipfile.ZipFile(archive) as z:
            selected=download['modem_candidates'];assert len(selected)==1
            member=z.getinfo(selected[0]['name'])
            assert member.file_size==selected[0]['bytes'] and member.file_size<=512*1024*1024
            image.write_bytes(z.read(member))
root=out/'firmware'
assert not root.exists(),'Use extracted metadata to resume; never replace reference files'
root.mkdir()
with (out/'mcopy-private.log').open('wb') as log:
    for glob in ('slpi.mdt','slpi.b*','slpi*.jsn'):
        subprocess.run(['mcopy','-i',str(image),'::/image/'+glob,str(root)],stdout=log,stderr=log,check=True,timeout=30)
def segments(path):
    data=path.read_bytes(); assert data[:6]==b'\x7fELF\x01\x01'
    off=struct.unpack_from('<I',data,28)[0]
    step,count=struct.unpack_from('<HH',data,42); assert step==32
    result=[]
    for i in range(count):
        kind,offset,va,pa,size,memsz,flags,align=struct.unpack_from('<IIIIIIII',data,off+i*step)
        if kind!=1 or not memsz or (flags>>24)&7==2: continue
        if size:
            split=path.parent/f'slpi.b{i:02d}'
            assert split.is_file() and split.stat().st_size==size
        result.append(dict(index=i,va=va,pa=pa,file_bytes=size,memory_bytes=memsz,flags=flags))
    return count,result
oldcount,old=segments(original/'slpi.mdt')
newcount,new=segments(root/'slpi.mdt')
versions=set(); terms=['lsm6dsm','lsm6ds3c','mmc5603','stk3331','I2C_QUP_DDR','SPI_QUP_DDR']; inventory={term:0 for term in terms}
hashes={}
for path in sorted(root.iterdir()):
    assert path.is_file() and re.fullmatch(r'slpi\.(mdt|b\d\d)|slpi[^/]*\.jsn',path.name)
    data=path.read_bytes(); hashes[path.name]=hashlib.sha256(data).hexdigest()
    versions.update(m.decode('ascii') for m in re.findall(rb'SLPI\.HY\.[A-Za-z0-9._-]+',data))
    for term in terms: inventory[term]+=data.lower().count(term.lower().encode())
old_low=min(s['pa'] for s in old);old_high=max(s['pa']+s['memory_bytes'] for s in old)
new_low=min(s['pa'] for s in new);new_high=max(s['pa']+s['memory_bytes'] for s in new)
same_ranges=[(s['pa'],s['memory_bytes']) for s in new]==[(s['pa'],s['memory_bytes']) for s in old]
report=dict(firmware_versions=sorted(versions),program_headers=newcount,load_segments=len(new),
            identical_to_original_slpi=all((original/name).exists() and hashlib.sha256((original/name).read_bytes()).hexdigest()==digest for name,digest in hashes.items()),
            split_file_sizes_match_mdt=True,files=hashes,
            same_physical_segment_layout=same_ranges,
            candidate_span_bytes=new_high-new_low,original_span_bytes=old_high-old_low,
            same_linked_base=new_low==old_low,candidate_span_fits_original=new_high-new_low<=old_high-old_low,
            driver_string_inventory=inventory,linux_deployed=False,sensors_accepted=False,
            modem_image_only_inspected_offline=True,package_scripts_executed=False)
(out/'segments-private.json').write_text(json.dumps(new,indent=2)+'\n')
(root/'SHA256SUMS').write_text(''.join(f'{digest}  {name}\n' for name,digest in hashes.items()))
(ref/(variant+'-reference-validation.json')).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='files'}))
