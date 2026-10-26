"""Read retained candidate bytes and receipts only; never executes a packer."""
from pathlib import Path
import hashlib
import json
import lzma
import struct
import uuid
import zlib

HERE=Path(__file__).resolve().parent
REF=HERE.parents[1]
OUT=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/eud-boot-two-ffs-candidate-private-01')
sha=lambda b:hashlib.sha256(b).hexdigest()
record_raw=(OUT/'result.json').read_bytes();record=json.loads(record_raw)
assert sha(record_raw)=='6dafe9e10877973d62b4348fdded0236ef47944e121d10ae2da96a9e84787b44'
assert record['passed'] and len(record['commands'])==12 and all(c.get('returncode')==0 for c in record['commands'])
assert record['inputs_before']==record['inputs_after'] and record['parent_inputs_unchanged'] and record['parent_mountinfo_unchanged']
source=REF/'charging-session-20261023/eud-boot-two-ffs-candidate/package.py'
assert sha(source.read_bytes())=='f8e9a8aeb7b92c87be4cf66f8a99d950b6247146cf913b5971734bf496d141bf'
assert record['inputs_before'][str(source)]==sha(source.read_bytes())
for name,digest in record['artifacts'].items():assert sha((OUT/name).read_bytes())==digest,name
manifest=REF/'charging-session-20261023/eud-boot-packaging-review/inspection.json'
assert sha(manifest.read_bytes())=='2caa68c513fd7503e0357aa4eb392594c906c82133c6e8d5d1fd3c3e703a3b87'
m=json.loads(manifest.read_bytes())
parser=REF/'kernel104/verify-firmware.py'
assert sha(parser.read_bytes())=='2e0b03aa3cf7ae7651e0b2e1153c1c5eb0cba3a3b41ef1d375c9b06358cb9d5d'
ns={};exec(compile(parser.read_text().split('\ndt_audit=',1)[0],'<sealed-fv-definitions>','exec'),ns)
fv,sections,align=ns['fv'],ns['sections'],ns['align']
SEC='8af09f13-44c5-96ec-1437-dd899cb5ee5d'
BDS='6d33944a-ec75-4855-a54d-809c75241f6c'
DTB='25462cda-221f-47df-ac1d-259cfaa4e326'
CONTAINER='9e21fd93-9c72-4c15-8c4b-e77f1db2d792'
LIMIT=6686720;TOTAL=100663296
def complete_files(volume):
    fv(volume)
    off=align(struct.unpack_from('<H',volume,48)[0],8);out={}
    while off+24<=len(volume) and volume[off:off+24]!=b'\xff'*24:
        attrs=volume[off+19];size=int.from_bytes(volume[off+20:off+23],'little')
        if attrs&1:size=struct.unpack_from('<Q',volume,off+24)[0]
        if volume[off+18]!=0xf0:
            name=str(uuid.UUID(bytes_le=volume[off:off+16]));assert name not in out
            out[name]={'offset':off,'bytes':volume[off:off+size]}
        off=align(off+size,8)
    return out
def parse_boot(blob):
    assert len(blob)==TOTAL and blob[:8]==b'ANDROID!'
    ks,rs,ss,page,version=[struct.unpack_from('<I',blob,at)[0] for at in [8,16,24,36,40]]
    assert (rs,ss,page,version)==(1,0,2048,1)
    ram_at=page+align(ks,page);used=ram_at+align(rs,page)
    payload=blob[page:page+ks];ram=blob[ram_at:ram_at+rs]
    h=hashlib.sha1()
    for piece in [payload,ram]:h.update(piece);h.update(struct.pack('<I',len(piece)))
    h.update(struct.pack('<II',0,0));assert blob[576:608]==h.digest()+b'\0'*12
    gzip=zlib.decompressobj(31);raw=gzip.decompress(payload)+gzip.flush()
    assert gzip.eof and not gzip.unconsumed_tail and len(raw)==7340176
    compat=gzip.unused_data;gz=payload[:-len(compat)]
    assert struct.unpack('<II',gz[-8:])==(zlib.crc32(raw)&0xffffffff,len(raw))
    fd=raw[144:];outer=fv(fd);assert len(fd)==7340032
    assert list(outer)==[SEC,CONTAINER]
    typ,body,section=outer[CONTAINER]['sections'][0]
    assert len(outer[CONTAINER]['sections'])==1 and typ==2
    assert str(uuid.UUID(bytes_le=body[:16]))==m['compression']['guided_guid']
    offset,attrs=struct.unpack_from('<HH',body,16);assert (offset,attrs)==(24,1)
    inner=sections(lzma.decompress(section[offset:],format=lzma.FORMAT_ALONE))
    assert len(inner)==1 and inner[0][0]==0x17
    return {'ks':ks,'used':used,'ram_at':ram_at,'ram':ram,'ram_page':blob[ram_at:used],
        'payload':payload,'gzip':gz,'compat':compat,'raw':raw,'fd':fd,'main':inner[0][1]}
original=Path(m['rollback']['path']).read_bytes();candidate=(OUT/'boot-two-ffs-private.img').read_bytes()
assert sha(original)==m['rollback']['sha256']=='a30fb4440726e1c3ab80ad65277db4e57fec9a0924380cc07830a5c6e69ec280'
assert sha(candidate)==record['boot_sha256']=='4126a2978bc79b5cb95b6e1b86bb432a6b16ece627776237c163b93b323bbfcf'
old,new=parse_boot(original),parse_boot(candidate)
assert old['used']==LIMIT and new['used']==record['new_used']==6684672<=LIMIT
assert new['ks']==record['new_kernel_size']==6679007
assert new['raw']==(OUT/'raw.bin').read_bytes() and new['gzip']==(OUT/'raw.gz').read_bytes()
assert new['fd']==(OUT/'compact.fd').read_bytes() and new['main']==(OUT/'main.Fv').read_bytes()
assert new['raw'][:144]==old['raw'][:144]
assert new['gzip'][:10]==old['gzip'][:10] and new['compat']==old['compat']
assert sha(new['compat'])==m['android']['compat_sha256']
assert new['ram']==old['ram']==b'\n' and new['ram_page']==old['ram_page']
assert candidate[2048+new['ks']:new['ram_at']]==b'\0'*(new['ram_at']-2048-new['ks'])
headers=[bytearray(blob[:2048]) for blob in [original,candidate]]
for header in headers:header[8:12]=b'\0'*4;header[576:608]=b'\0'*32
assert headers[0]==headers[1]
assert candidate[new['used']:]==original[new['used']:] and candidate[LIMIT:]==original[LIMIT:]
assert any(original[LIMIT:]) and sha(candidate[LIMIT:])==m['android']['tail_sha256']
old_outer,new_outer=complete_files(old['fd']),complete_files(new['fd'])
assert new_outer[SEC]['offset']==old_outer[SEC]['offset']==0xfe8
assert new_outer[SEC]['bytes']==old_outer[SEC]['bytes']
assert new_outer[CONTAINER]['offset']==old_outer[CONTAINER]['offset']
hl=struct.unpack_from('<H',new['fd'],48)[0]
assert hl==struct.unpack_from('<H',old['fd'],48)[0] and new['fd'][:hl]==old['fd'][:hl]
a,b=complete_files(old['main']),complete_files(new['main'])
assert list(a)==list(b) and len(a)==101
changed=[name for name in a if a[name]['bytes']!=b[name]['bytes']]
assert changed==[BDS,DTB] and sum(a[name]['bytes']==b[name]['bytes'] for name in a)==99
om,nm=fv(old['main']),fv(new['main'])
for name in a:assert (om[name]['type'],om[name]['attrs'])==(nm[name]['type'],nm[name]['attrs'])
bs,prior=nm[BDS]['sections'],om[BDS]['sections']
assert [s[0] for s in bs]==[0x13,0x10,0x15]
assert bs[0][2]==prior[0][2] and bs[2][2]==prior[2][2]
efi=Path(m['candidate_EFI']['path']).read_bytes();dtb=Path(m['candidate_native_DTB']['path']).read_bytes()
assert sha(efi)=='a0e30c69b91f5605c07136f3f0c6900434f99d72159c5c61ac01db47fc061768' and bs[1][1]==efi
assert sha(dtb)=='9271d9cc33b3701ad0675c6345d43e9a5c404aa6c192126edc3eb715b0914358'
ds=nm[DTB]['sections'];assert len(ds)==1 and ds[0][0]==0x19 and ds[0][1]==dtb
report={'status':'actual candidate source/artifact/structure binding passed; not deployed',
    'reviewed_executor_sha256':sha(source.read_bytes()),'private_execution_result_sha256':sha(record_raw),
    'candidate_boot_sha256':sha(candidate),'candidate_bytes':len(candidate),'baseline_rollback_sha256':sha(original),
    'commands':[{'stage':c['stage'],'tool':Path(c['argv'][0]).name,'returncode':c['returncode']} for c in record['commands']],
    'artifact_hashes_checked':len(record['artifacts']),'parent_before_after_equal_count':len(record['inputs_before']),
    'mountinfo_unchanged_from_execution_receipt':record['parent_mountinfo_unchanged'],
    'independent_parse':{'Android_v1_ID_verified':True,'page':2048,'new_kernel_size':new['ks'],'new_used':new['used'],'old_used_limit':LIMIT,
        'header_only_kernel_size_and_ID':True,'gzip_CRC_EOF_ISIZE_verified':True,'raw_bytes':len(new['raw']),
        'gzip_header_unchanged':True,'shim_compat_full_ramdisk_page_unchanged':True,'absolute_newused_and_LIMIT_tails_unchanged':True,
        'old_LIMIT_tail_nonzero':True,'SEC_complete_FFS_bytes_unchanged':True,'SEC_offset':0xfe8,'compact_header_byte_exact':True,
        'container_position_unchanged':True,'exact_changed_FFS_labels':['BDS','native DTB'],'remaining_complete_FFS_equal':99,
        'all_FFS_order_type_attrs_preserved':True,'BDS_depex_UI_unchanged':True,'EFI_DTB_frozen_payloads_exact':True,
        'candidate_intermediate_raw_gzip_FD_main_match_boot':True},
    'candidate_product_evidence_not_old_baseline':True,'only_parser_definitions_reused':True,
    'packaging_tools_executed_by_reviewer':False,'check_local_or_old_baseline_rerun':False,'tests_rerun':False,
    'device_SSH_SDK_Git_used':False,'deployed':False,'boot_panel_EUD_route_USB500_acceptance':False}
(HERE/'product-review.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'passed':True,'product_review_sha256':sha((HERE/'product-review.json').read_bytes()),'candidate_boot_sha256':sha(candidate),'commands':12,'other_full_FFS_equal':99}))
