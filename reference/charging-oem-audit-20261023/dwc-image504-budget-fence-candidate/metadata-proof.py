"""ELF section/content proof only; in-memory comparison never patches artifacts."""
from pathlib import Path
import hashlib,struct
OLD_ID=b'#502 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026'
NEW_ID=b'#504 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026'
digest=lambda raw:hashlib.sha256(raw).hexdigest()
def elf(path):
    raw=Path(path).read_bytes()
    h=struct.unpack_from('<16sHHIQQQIHHHHHH',raw)
    assert h[0][:6]==b'\x7fELF\x02\x01' and h[2]==183
    sh=[struct.unpack_from('<IIQQQQIIQQ',raw,h[6]+i*h[11]) for i in range(h[12])]
    names=raw[sh[h[13]][4]:sh[h[13]][4]+sh[h[13]][5]]
    result={}
    for s in sh:
        name=names[s[0]:].split(b'\0',1)[0].decode()
        assert name not in result
        result[name]={'flags':s[2],'size':s[5],'offset':s[4],
                     'data':b'' if s[1]==8 else raw[s[4]:s[4]+s[5]]}
    return raw,result
def prove(original,candidate):
    reports={}
    for n in ['init/version.o','init/version-timestamp.o']:
        old,a=elf(original/n);new,b=elf(candidate/n)
        assert set(a)==set(b)
        assert len(old)==len(new) and old.count(OLD_ID)>0
        assert old.replace(OLD_ID,NEW_ID)==new,(n,'Unexpected bytes outside identity string')
        changed=[]
        for key in a:
            x,y=a[key],b[key]
            assert x['flags']==y['flags'] and x['size']==y['size'] and x['offset']==y['offset']
            if x['data']!=y['data']:
                assert key in ['.data','.rodata'] and OLD_ID in x['data']
                assert x['data'].replace(OLD_ID,NEW_ID)==y['data']
                changed.append({'section':key,'bytes':x['size'],'old_sha256':digest(x['data']),
                                'new_sha256':digest(y['data']),'identity_substitution_only':True})
            if x['flags']&4:assert x['data']==y['data']
        reports[n]={'old_sha256':digest(old),'new_sha256':digest(new),'changed_sections':changed,
                    'identity_occurrences':old.count(OLD_ID),'whole_object_identity_substitution_only':True,
                    'all_executable_sections_identical':True,'all_other_sections_identical':True,
                    'no_artifact_bytes_written':True}
    return {'passed':True,'old_identity':OLD_ID.decode(),'new_identity':NEW_ID.decode(),
            'timestamp_semantics':'original explicit reproducible timestamp, actual execution UTC recorded separately',
            'objects':reports,'comparison_only':True}
