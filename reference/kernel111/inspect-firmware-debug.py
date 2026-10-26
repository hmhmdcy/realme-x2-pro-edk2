from pathlib import Path
import hashlib,json,struct
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel104/verify-firmware.py')
ns={};exec(compile(ref.read_text().split('dt_audit=')[0],'firmware-helpers','exec'),ns)
out=Path('/mnt/e/edk2-samurai-out/kernel111')
old=ns['fv']((out/'fvmain-before.Fv').read_bytes())
new=ns['fv']((out/'fvmain-after.Fv').read_bytes())
results=[]
def pe_sections(b):
    assert b[:2]==b'MZ'
    start=struct.unpack_from('<I',b,0x3c)[0]
    assert b[start:start+4]==b'PE\0\0'
    count=struct.unpack_from('<H',b,start+6)[0]
    opt=struct.unpack_from('<H',b,start+20)[0]
    offset=start+24+opt
    sections={}
    for i in range(count):
        rec=b[offset+40*i:offset+40*(i+1)]
        name=rec[:8].rstrip(b'\0').decode()
        size,pointer=struct.unpack_from('<II',rec,16)
        sections[name]=b[pointer:pointer+size]
    return sections
for guid,m in old.items():
    n=new[guid]
    if m['body']==n['body'] or guid==ns['dt_guid']:continue
    a=[s[1] for s in m['sections'] if s[0]==0x10]
    b=[s[1] for s in n['sections'] if s[0]==0x10]
    assert len(a)==len(b)==1
    sa,sb=pe_sections(a[0]),pe_sections(b[0])
    results.append(dict(name=n['name'],text_same=sa.get('.text')==sb.get('.text'),
                        old_path_present=b'/home/cy122/edk2-samurai/repo' in a[0],
                        new_path_present=b'/home/cy122/pmos-samurai-kernel111/edk2' in b[0],
                        rsds_debug_present=b'RSDS' in a[0] and b'RSDS' in b[0]))
(out/'firmware-debug-path-analysis.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(dict(changed_executables=len(results),text_section_same=sum(r['text_same'] for r in results),
                     with_changed_build_path=sum(r['old_path_present'] and r['new_path_present'] for r in results),
                     all_rsds_debug_present=all(r['rsds_debug_present'] for r in results))))
