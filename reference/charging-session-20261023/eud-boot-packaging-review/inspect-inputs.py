"""Read-only geometry/input inspection. Does not run any firmware packaging tool."""
from pathlib import Path
import hashlib,json,lzma,re,struct,uuid,zlib

repo=Path('/home/cy122/edk2-samurai/repo')
workspace=Path('/mnt/e/RealmeX2Pro edk2')
own=workspace/'reference/charging-session-20261023/eud-boot-packaging-review'
root=Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
old=root/'usb-boot'
build=repo/'workspace/Build/samurai/RELEASE_GCC5/FV'
sha=lambda b:hashlib.sha256(b).hexdigest()
def record(p):
    b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':sha(b)}
scope={}
parser=workspace/'reference/kernel104/verify-firmware.py'
exec(compile(parser.read_text().split('\ndt_audit=',1)[0],str(parser)+':definitions-only','exec'),scope)
fv,sections,align=scope['fv'],scope['sections'],scope['align']
boot_path=old/'boot-charging-usb-dt.img';boot=boot_path.read_bytes()
assert sha(boot)=='a30fb4440726e1c3ab80ad65277db4e57fec9a0924380cc07830a5c6e69ec280'
ks,rs,ss,page,version=[struct.unpack_from('<I',boot,p)[0] for p in [8,16,24,36,40]]
assert (rs,ss,page,version)==(1,0,2048,1)
payload=boot[page:page+ks];d=zlib.decompressobj(31);raw=d.decompress(payload)+d.flush()
assert d.eof and not d.unconsumed_tail
compat=d.unused_data;gz=payload[:-len(compat)]
fd=raw[144:];outer=fv(fd)
container=next(m for m in outer.values() if m['type']==0xb)
_,guided_body,guided_section=container['sections'][0]
data_offset,attrs=struct.unpack_from('<HH',guided_body,16)
compressed=guided_section[data_offset:]
decoded=lzma.decompress(compressed,format=lzma.FORMAT_ALONE)
nested=sections(decoded);assert len(nested)==1 and nested[0][0]==0x17
main=nested[0][1];inner=fv(main)
def raw_files(volume):
    result=[];off=align(struct.unpack_from('<H',volume,48)[0],8)
    while off+24<=len(volume) and volume[off:off+24]!=b'\xff'*24:
        attrs=volume[off+19];size=int.from_bytes(volume[off+20:off+23],'little')
        header_size=24
        if attrs&1:size=struct.unpack_from('<Q',volume,off+24)[0];header_size=32
        full=volume[off:off+size]
        if volume[off+18]!=0xf0:
            head=bytearray(full[:header_size]);head[17]=head[23]=0
            assert sum(head)%256==0
            stand=bytearray(full);stand[23]^=0xff
            sh=bytearray(stand[:header_size]);sh[17]=sh[23]=0
            assert sum(sh)%256==0
            result.append({'guid':str(uuid.UUID(bytes_le=full[:16])),'offset':off,'bytes':size,
                           'header_size':header_size,'state_in_FV':full[23],'standalone_state':stand[23],
                           'sha256':sha(full),'standalone_sha256':sha(stand),'body_sha256':sha(full[header_size:])})
        off=align(off+size,8)
    return result
def config_inputs(name,actual):
    config=build/(name+'.inf');paths=[Path(l.split('=',1)[1].strip()) for l in config.read_text().splitlines() if l.startswith('EFI_FILE_NAME')]
    values=[]
    for p in paths:
        data=p.read_bytes();guid=str(uuid.UUID(bytes_le=data[:16]));match=next(v for v in actual if v['guid']==guid)
        values.append(dict(record(p),guid=guid,body_equal_a30=sha(data[match['header_size']:])==match['body_sha256'],
                           equals_state_normalized_a30=sha(data)==match['standalone_sha256']))
    assert [v['guid'] for v in values]==[v['guid'] for v in actual]
    return {'config':record(config),'inputs':values}
main_files,outer_files=raw_files(main),raw_files(fd)
used=page+align(ks,page)+align(rs,page)
ramdisk=boot[page+align(ks,page):page+align(ks,page)+rs]
h=hashlib.sha1()
for piece in [payload,ramdisk]:h.update(piece);h.update(struct.pack('<I',len(piece)))
for _ in range(2):h.update(struct.pack('<I',0))
assert boot[576:608]==h.digest()+b'\0'*12
native=root/'eud-boot-policy-private/samurai-eud-off-policy-private.dtb'
efi=root/'eud-bds-r2-private-01/BdsDxe/OUTPUT/BdsDxe.efi'
assert sha(native.read_bytes())=='9271d9cc33b3701ad0675c6345d43e9a5c404aa6c192126edc3eb715b0914358'
assert sha(efi.read_bytes())=='a0e30c69b91f5605c07136f3f0c6900434f99d72159c5c61ac01db47fc061768'
saved_main=old/'firmware/fvmain-candidate-private.Fv';saved_fd=old/'firmware/firmware-candidate-private.fd'
assert saved_main.read_bytes()==main and saved_fd.read_bytes()==fd
tools=[repo/'Common/edk2/BaseTools/Source/C/bin'/n for n in ['GenSec','GenFfs','GenFv','LzmaCompress']]+[Path('/usr/bin/gzip')]
raw_cache=build/'SM8150_UEFI.fd-bootshim'
sources=[repo/p for p in ['Silicon/platform.sh.inc','tools/mkbootimg.py','Platform/Qualcomm/sm8150/sm8150.fdf',
         'Common/edk2/BaseTools/Source/C/GenFv/GenFvInternalLib.c','Common/edk2/BaseTools/Source/C/GenFv/GenFv.c',
         'Common/edk2/BaseTools/Source/Python/GenFds/GenFdsGlobalVariable.py','Common/edk2/BaseTools/Source/Python/GenFds/GuidSection.py']]
result={'scope':'plan/input inspection only; no packing command executed','rollback':record(boot_path),
        'candidate_EFI':record(efi),'candidate_native_DTB':record(native),'saved_main_FV':record(saved_main),'saved_compact_FD':record(saved_fd),
        'shared_main_FV_matches_a30':(build/'FVMAIN.Fv').read_bytes()==main,
        'cached_raw':dict(record(raw_cache),equals_a30_raw=raw_cache.read_bytes()==raw,mtime_ns=raw_cache.stat().st_mtime_ns),
        'main_FV':{'bytes':len(main),'filesystem_guid':str(uuid.UUID(bytes_le=main[16:32])),'blockmap':struct.unpack_from('<II',main,56),'files':main_files},
        'compact_FV':{'bytes':len(fd),'filesystem_guid':str(uuid.UUID(bytes_le=fd[16:32])),'blockmap':struct.unpack_from('<II',fd,56),'files':outer_files},
        'main_config':config_inputs('FVMAIN',main_files),'compact_config':config_inputs('FVMAIN_COMPACT',outer_files),
        'compression':{'guided_guid':str(uuid.UUID(bytes_le=guided_body[:16])),'data_offset':data_offset,'attributes':attrs,
                       'LZMA_header_hex':compressed[:13].hex(),'compressed_bytes':len(compressed),'decoded_bytes':len(decoded),'nested_FV_section_header_bytes':len(decoded)-len(main)},
        'android':{'kernel_payload_bytes':ks,'kernel_payload_sha256':sha(payload),'raw_sha256':sha(raw),'gzip_sha256':sha(gz),
                   'used_boot_bytes':used,'partition_bytes':len(boot),'page':page,'version':version,
                   'header_page_sha256':sha(boot[:page]),'ramdisk_hex':ramdisk.hex(),'shim_sha256':sha(raw[:144]),
                   'compat_bytes':len(compat),'compat_sha256':sha(compat),'gzip_header_hex':gz[:10].hex(),
                   'gzip_mtime':struct.unpack_from('<I',gz,4)[0],'gzip_crc32':hex(struct.unpack_from('<I',gz,len(gz)-8)[0]),
                   'gzip_isize':struct.unpack_from('<I',gz,len(gz)-4)[0],'Android_ID_formula_verified':True,
                   'tail_sha256':sha(boot[used:]),'tail_has_nonzero_bytes':any(boot[used:]),
                   'tail_first_nonzero_absolute_offset':next((i for i in range(used,len(boot)) if boot[i]),None)},
        'tools':[record(p) for p in tools],'source_rules':[record(p) for p in sources],
        'packing_executed':False,'device_accessed':False}
write=lambda p,v:p.write_text(json.dumps(v,indent=2)+'\n')
write(own/'inspection.json',result)
print(json.dumps({'main_file_count':len(main_files),'main_nonidentical_cached_FFS':[v['guid'] for v in result['main_config']['inputs'] if not v['equals_state_normalized_a30']],
                  'compact_nonidentical_cached_FFS':[v['guid'] for v in result['compact_config']['inputs'] if not v['equals_state_normalized_a30']],
                  'main_fs':result['main_FV']['filesystem_guid'],'compact_fs':result['compact_FV']['filesystem_guid'],'compression':result['compression'],'android':result['android']},indent=2))
