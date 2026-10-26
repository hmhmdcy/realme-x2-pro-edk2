"""Read retained carrier bytes; no packer entry, subprocess, build or device API."""
from pathlib import Path
import ast
import hashlib
import json
import lzma
import struct
import uuid
import zlib

HERE=Path(__file__).resolve().parent
REF=HERE.parents[1]
AUTHOR=REF/'charging-session-20261023/gauge-image501-carriers-candidate'
ROOT=Path('E:/edk2-samurai-out/charging-management-20261023')
sha=lambda b:hashlib.sha256(b).hexdigest()
delivery_raw=(AUTHOR/'delivery.json').read_bytes();delivery=json.loads(delivery_raw)
assert sha(delivery_raw)=='9dd01720a4f514d002a12d2344e7b644b07239a78bdb858f819508fcf3952850'
for name,pin in delivery['files'].items():
    raw=(AUTHOR/name).read_bytes();assert len(raw)==pin['bytes'] and sha(raw)==pin['sha256'],name
receipts={}
for name,pin in delivery['private_receipts'].items():
    raw=Path(pin['path']).read_bytes();assert sha(raw)==pin['sha256'];r=json.loads(raw)
    assert r['passed']
    commands=r.get('commands',r.get('child',{}).get('commands',[]))
    assert commands and all(c.get('returncode')==0 for c in commands)
    receipts[name]={'sha256':sha(raw),'terminal_commands':[{'stage':c['stage'],'returncode':c['returncode']} for c in commands]}
art={}
for name,pin in delivery['private_artifacts'].items():
    raw=Path(pin['path']).read_bytes();assert len(raw)==pin['bytes'] and sha(raw)==pin['sha256'],name;art[name]=raw

# Only the already-reviewed definitions, without importing an executable packer.
parser=REF/'kernel104/verify-firmware.py'
assert sha(parser.read_bytes())=='2e0b03aa3cf7ae7651e0b2e1153c1c5eb0cba3a3b41ef1d375c9b06358cb9d5d'
env={};exec(compile(parser.read_text().split('\ndt_audit=',1)[0],'<sealed-parser>','exec'),env)
fv,sections,align=env['fv'],env['sections'],env['align']
manifest=REF/'charging-session-20261023/eud-boot-packaging-review/inspection.json'
m=json.loads(manifest.read_bytes())
old_review=HERE.parent/'eud-boot-packaging-r2-review/review-product.py'
tree=ast.parse(old_review.read_text())
scope=dict(Path=Path,hashlib=hashlib,json=json,lzma=lzma,struct=struct,uuid=uuid,zlib=zlib,sha=sha,
           fv=fv,sections=sections,align=align,m=m,TOTAL=100663296,SEC='8af09f13-44c5-96ec-1437-dd899cb5ee5d',CONTAINER='9e21fd93-9c72-4c15-8c4b-e77f1db2d792')
definitions=ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['complete_files','parse_boot']],type_ignores=[])
exec(compile(definitions,'<prior-reviewed-readonly-functions>','exec'),scope)
a,b=scope['parse_boot'](art['rollback_boot']),scope['parse_boot'](art['candidate_boot'])
assert a['used']==b['used']==6684672 and b['ks']==6680472
assert a['raw'][:144]==b['raw'][:144] and a['compat']==b['compat'] and a['ram_page']==b['ram_page']
assert a['gzip'][:10]==b['gzip'][:10] and art['rollback_boot'][a['used']:]==art['candidate_boot'][b['used']:]
headers=[bytearray(art[n][:2048]) for n in ['rollback_boot','candidate_boot']]
for h in headers:h[8:12]=b'\0'*4;h[576:608]=b'\0'*32
assert headers[0]==headers[1]
files=[scope['complete_files'](x['main']) for x in [a,b]]
BDS='6d33944a-ec75-4855-a54d-809c75241f6c';DTB='25462cda-221f-47df-ac1d-259cfaa4e326'
changed=[g for g in files[0] if files[0][g]['bytes']!=files[1][g]['bytes']]
assert list(files[0])==list(files[1]) and len(files[0])==101 and changed==[BDS]
outer=[scope['complete_files'](x['fd']) for x in [a,b]]
SEC=scope['SEC'];assert outer[0][SEC]==outer[1][SEC] and outer[0][SEC]['offset']==0xfe8
mods=[fv(x['main']) for x in [a,b]]
assert [s[0] for s in mods[1][BDS]['sections']]==[0x13,0x10,0x15]
for n in [0,2]:assert mods[0][BDS]['sections'][n][2]==mods[1][BDS]['sections'][n][2]
efi=art['BDS_EFI'];assert mods[1][BDS]['sections'][1][1]==efi
dtb=mods[1][DTB]['sections'][0][1];assert sha(dtb)==delivery['native_DTB_sha256']=='9271d9cc33b3701ad0675c6345d43e9a5c404aa6c192126edc3eb715b0914358'
assert efi[:2]==b'MZ';pe=struct.unpack_from('<I',efi,0x3c)[0];assert efi[pe:pe+4]==b'PE\0\0'
assert struct.unpack_from('<H',efi,pe+4)[0]==0xaa64 and struct.unpack_from('<H',efi,pe+24)[0]==0x20b
oldcmd='console=tty0 loglevel=7 ignore_loglevel panic=15 clk_ignore_unused pd_ignore_unused regulator_ignore_unused'
newcmd=oldcmd+' bq27xxx_battery.samurai_instant_current=1'
assert (newcmd+'\0').encode('utf-16-le') in efi
assert b'[SAMURAI-EUD-OFF] attempted=%u write=%u arm=%08x before=%08x after=%08x status=%r' in efi
oldsource=(REF/'charging-oem-audit-20261023/eud-boot-policy-r2/PlatformBm.c.candidate').read_bytes()
newsource=(AUTHOR/'PlatformBm.c.candidate').read_bytes()
assert sha(oldsource)=='c1ce63b3cc8df1c44b5351f53d15294505df919915fa8773636054305617cee8'
assert oldsource.replace(('L"'+oldcmd+'"').encode(),('L"'+newcmd+'"').encode(),1)==newsource

fat_tree=ast.parse((AUTHOR/'package-logdump.py').read_text())
fat_scope={'struct':struct,'sha':sha}
exec(compile(ast.Module(body=[n for n in fat_tree.body if isinstance(n,ast.FunctionDef) and n.name=='parse_fat'],type_ignores=[]),'<actual-readonly-FAT-parser>','exec'),fat_scope)
fa,fb=[fat_scope['parse_fat'](art[n]) for n in ['rollback_logdump','candidate_logdump']]
assert fb['files']['Image']['sha256']==delivery['Image501_sha256']=='3a656c75d3b714153d77b637654c894a0418fd688cc906d59a37a41401e8cc02'
assert fb['files']['Image']['size']==59243008
assert fa['files']['SAMURAI.DTB']==fb['files']['SAMURAI.DTB']
# Verify all bytes outside old/new Image data, its own directory and FAT chain.
ranges=[]
for f in [fa,fb]:
    image=f['files']['Image']
    for n in image['clusters']:
        ranges.append((f['data_at']+(n-2)*f['bps'],f['data_at']+(n-1)*f['bps']))
        for copy in [0,1]:
            p=f['fat_at']+copy*f['fat_size']+n*2;ranges.append((p,p+2))
    for p in image['entry_offsets']:ranges.append((p,p+32))
merged=[]
for start,end in sorted(ranges):
    if merged and start<=merged[-1][1]:merged[-1][1]=max(end,merged[-1][1])
    else:merged.append([start,end])
last=0;old,new=art['rollback_logdump'],art['candidate_logdump']
for start,end in merged:assert old[last:start]==new[last:start];last=end
assert old[last:]==new[last:]
r={'passed':True,'scope':'existing two carriers only; independent read-only parse, not a new build or deployment',
   'author_delivery_sha256':sha(delivery_raw),'receipt_commands':receipts,
   'boot_sha256':sha(art['candidate_boot']),'logdump_sha256':sha(new),
   'boot':{'only_BDS_complete_FFS_changed':True,'other_complete_FFS_equal':100,'BDS_depex_UI_equal':True,'native_DTB_sha256':sha(dtb),
           'SEC_complete_offset_equal':True,'SEC_offset':0xfe8,'shim_compat_ramdisk_tail_equal':True,'header_only_size_ID_changes':True,'Android_ID_verified':True,'used':b['used'],'kernel_payload_bytes':b['ks']},
   'PE':{'sha256':sha(efi),'ARM64_PE32plus':True,'exact_full_UTF16_LoadOptions':True,'source_only_one_cmdline_addition':True,'EUD_marker_preserved':True},
   'FAT':{'Image_sha256':fb['files']['Image']['sha256'],'Image_bytes':fb['files']['Image']['size'],'other_file_exact':True,'every_non_Image_byte_equal':True},
   'ABI_reused_review_sha256':sha((HERE.parent/'gauge-image501-independent-review/review.json').read_bytes()),
   'build_or_tools_executed':False,'ABI_tests_rerun':False,'device_SDK_Git_used':False,'runtime_acceptance':False}
(HERE/'review.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({'passed':True,'review_sha256':sha((HERE/'review.json').read_bytes()),'boot':r['boot_sha256'],'logdump':r['logdump_sha256']}))
