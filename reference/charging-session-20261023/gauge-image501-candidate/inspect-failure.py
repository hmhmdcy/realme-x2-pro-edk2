"""Read-only ELF/CPIO attribution for the rejected B501 build. No rewriting."""
from pathlib import Path
import collections, gzip, hashlib, json, struct, sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
BASE=Path('/home/cy122/charging-management-20261023/gauge-image363-baseline-01')
OUT=Path('/home/cy122/charging-management-20261023/gauge-image501-B-01')
OLD=BASE/'build';NEW=OUT/'build'
digest=lambda b:hashlib.sha256(b).hexdigest()
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
assert json.loads((OUT/'namespace-process.json').read_bytes())['terminal']
assert json.loads((OUT/'result.json').read_bytes())['child_returncode']==1
def elf(path):
    raw=path.read_bytes();h=struct.unpack_from('<16sHHIQQQIHHHHHH',raw)
    assert h[0][:6]==b'\x7fELF\x02\x01' and h[2]==183
    sh=[struct.unpack_from('<IIQQQQIIQQ',raw,h[6]+i*h[11]) for i in range(h[12])]
    names=raw[sh[h[13]][4]:sh[h[13]][4]+sh[h[13]][5]]
    sections={}
    for i,s in enumerate(sh):
        n=names[s[0]:].split(b'\0',1)[0].decode()
        data=b'' if s[1]==8 else raw[s[4]:s[4]+s[5]]
        sections[n]={'index':i,'type':s[1],'offset':s[4],'size':s[5],'data':data,'header':s}
    symbols={}
    for sec in sections.values():
        s=sec['header']
        if s[1]!=2:continue
        table=sh[s[6]];strings=raw[table[4]:table[4]+table[5]]
        for off in range(s[4],s[4]+s[5],s[9]):
            a,b,c,d,e,f=struct.unpack_from('<IBBHQQ',raw,off)
            name=strings[a:].split(b'\0',1)[0].decode()
            if name:
                section=next((n for n,v in sections.items() if v['index']==d),None)
                symbols[name]={'info':b,'other':c,'section':section,'value':e,'size':f}
    return raw,sections,symbols
identity=json.loads((OUT/'identity.json').read_bytes())
old_identity=b'#363 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026'
new_identity=('#501 SMP PREEMPT '+identity['KBUILD_BUILD_TIMESTAMP']).encode()
def section_diff(relative):
    a,sa,ya=elf(OLD/relative);b,sb,yb=elf(NEW/relative)
    rows=[]
    for name in sorted(sa.keys()|sb.keys()):
        x,y=sa.get(name),sb.get(name)
        if x and y and x['data']==y['data'] and x['size']==y['size']:continue
        row={'name':name,'old_size':x['size'] if x else None,'new_size':y['size'] if y else None,
             'old_sha256':digest(x['data']) if x else None,'new_sha256':digest(y['data']) if y else None}
        if x and y:
            row['identity_substitution_only']=old_identity in x['data'] and x['data'].replace(old_identity,new_identity)==y['data']
        rows.append(row)
    symbol_rows={}
    for n in ['init_uts_ns','linux_banner','__initramfs_start','__initramfs_size']:
        if n not in ya or n not in yb:continue
        x,y=ya[n],yb[n]
        def body(sym,sec):
            return sec[sym['section']]['data'][sym['value']:sym['value']+sym['size']] if sym['section'] else b''
        xdata,ydata=body(x,sa),body(y,sb)
        symbol_rows[n]={'old':x,'new':y,'old_data_sha256':digest(xdata),'new_data_sha256':digest(ydata),
                        'identity_substitution_only':old_identity in xdata and xdata.replace(old_identity,new_identity)==ydata}
    text_same=all(sa[n]['data']==sb[n]['data'] for n in sa if n in sb and (sa[n]['header'][2]&4))
    return {'old_sha256':digest(a),'new_sha256':digest(b),'changed_sections':rows,
            'executable_sections_identical':text_same,'symbols':symbol_rows}
def cpio(raw):
    result=[];off=0
    while raw[off:off+6] in [b'070701',b'070702']:
        header=raw[off:off+110];fields=[int(header[6+i*8:14+i*8],16) for i in range(13)]
        ino,mode,uid,gid,nlink,mtime,size,major,minor,rmajor,rminor,namesize,check=fields
        name=raw[off+110:off+110+namesize];assert name[-1:]==b'\0'
        start=(off+110+namesize+3)&~3;end=start+size
        row={'name':name[:-1].decode(),'header_offset':off,'mtime':mtime,'fields':fields,
             'data_sha256':digest(raw[start:end]),'mtime_byte_range':[off+46,off+54]}
        result.append(row);off=(end+3)&~3
        if name==b'TRAILER!!!\0':break
    assert result and result[-1]['name']=='TRAILER!!!'
    return result,raw[off:]
a=(OLD/'usr/initramfs_data.cpio').read_bytes();b=(NEW/'usr/initramfs_data.cpio').read_bytes()
entries_a,tail_a=cpio(a);entries_b,tail_b=cpio(b)
assert len(entries_a)==len(entries_b)
changes=[];masked_a=bytearray(a);masked_b=bytearray(b)
for x,y in zip(entries_a,entries_b):
    assert x['name']==y['name'] and x['header_offset']==y['header_offset']
    fields=[i for i,(v,w) in enumerate(zip(x['fields'],y['fields'])) if v!=w]
    if fields or x['data_sha256']!=y['data_sha256']:
        changes.append({'name':x['name'],'header_offset':x['header_offset'],'changed_field_indices':fields,
                        'old_mtime':x['mtime'],'new_mtime':y['mtime'],'data_identical':x['data_sha256']==y['data_sha256']})
    lo,hi=x['mtime_byte_range'];masked_a[lo:hi]=b'0'*8;masked_b[lo:hi]=b'0'*8
save(OUT/'cpio-entry-differences.json',changes)
whitelist=['init','bin/busybox','lib/modules/samurai/hci_uart.ko','lib/modules/samurai/btqca.ko','lib/modules/samurai/btbcm.ko']
gzip_a=(OLD/'usr/initramfs_inc_data').read_bytes();gzip_b=(NEW/'usr/initramfs_inc_data').read_bytes()
assert gzip.decompress(gzip_a)==a and gzip.decompress(gzip_b)==b
version=section_diff('init/version.o')
ramfs=section_diff('usr/initramfs_data.o')
for label,root,compressed in [('old',OLD,gzip_a),('new',NEW,gzip_b)]:
    _,sections,_=elf(root/'usr/initramfs_data.o')
    ramfs[label+'_compressed_prefix_matches_section']=sections['.init.ramfs']['data'].startswith(compressed)
result={'status':'rejected candidate; read-only attribution only','artifact_rewritten':False,
 'old_identity':old_identity.decode(),'new_identity':new_identity.decode(),
 'version_object':version,'initramfs_object':ramfs,
 'cpio':{'old_bytes':len(a),'new_bytes':len(b),'old_sha256':digest(a),'new_sha256':digest(b),
         'entry_count':len(entries_a),'changed_entry_count':len(changes),'all_data_payloads_identical':all(r['data_identical'] for r in changes),
         'only_mtime_header_field_changed':all(r['changed_field_indices']==[5] for r in changes),
         'all_bytes_outside_mtime_fields_identical':masked_a==masked_b,'tail_identical':tail_a==tail_b,
         'old_mtime_counts':dict(collections.Counter(x['mtime'] for x in entries_a)),
         'new_mtime_counts':dict(collections.Counter(x['mtime'] for x in entries_b)),
         'selected_entries':[r for r in changes if r['name'] in whitelist],
         'full_private_entry_diff_sha256':digest((OUT/'cpio-entry-differences.json').read_bytes())},
 'gzip':{'old_bytes':len(gzip_a),'new_bytes':len(gzip_b),'old_sha256':digest(gzip_a),'new_sha256':digest(gzip_b),
         'both_decode_to_actual_cpio':True,'headers_identical':gzip_a[:10]==gzip_b[:10],'old_header_hex':gzip_a[:10].hex(),'new_header_hex':gzip_b[:10].hex()},
 'source_evidence':{str(p.relative_to(OUT/'source354')):digest(p.read_bytes()) for p in [OUT/'source354/init/version.c',
 OUT/'source354/init/Makefile',OUT/'source354/usr/Makefile',OUT/'source354/usr/gen_initramfs.sh',OUT/'source354/usr/gen_init_cpio.c']},
 'source_section_conclusions':[
 'init/version.c includes version-timestamp.c and compiles weak init_uts_ns/linux_banner; init/Makefile uses requested version/time for utsversion-tmp.h.',
 'usr/Makefile puts KBUILD_BUILD_TIMESTAMP into gen_initramfs.sh -d; changed args force cpio regeneration even when input files are unchanged.' ],
 'device_access':False,'new_build_or_tests':False}
save(OUT/'failure-attribution.json',result);save(HERE/'failure-attribution.json',result)
print(json.dumps({'version_sections':version['changed_sections'],'version_executable_sections_identical':version['executable_sections_identical'],
 'version_symbols':version['symbols'],'initramfs_sections':ramfs['changed_sections'],'cpio':result['cpio'],'gzip':result['gzip']},indent=2),flush=True)
