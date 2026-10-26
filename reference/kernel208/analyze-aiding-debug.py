from pathlib import Path
import json,sys
sys.path.insert(0,'/var/lib/samurai/k208-loc-tools')
from pqwm1 import sentence
root=Path('/var/lib/samurai')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k208-baseline/boot-id-private.txt').read_bytes()
out=root/'k208-aiding-debug-analysis';out.mkdir(mode=0o700)
groups={'PQWP3':[],'PQWP4':[],'PQWP5':[]};seen=set();errors=0
for line in (root/'k208-mm-debug-observer/mm-nmea-private.jsonl').read_text().splitlines():
    for text in str(json.loads(line).get('4','')).replace('\r','').split('\n'):
        if text in seen or not text.startswith(('$PQWP3,','$PQWP4,','$PQWP5,')):continue
        seen.add(text)
        try:
            fields=sentence(text);groups[fields[0]].append(fields)
        except ValueError:errors+=1
constellations=['gps','glo','bds','gal','qzss']
result=dict(stage=208,same_saved_session_only=True,no_new_gps_or_injection=True,checksum_errors=errors,reports={name:len(values) for name,values in groups.items()})
if groups['PQWP3']:
    assert all(len(fields)>=13 for fields in groups['PQWP3'])
    result['xtra_valid_mask_values']=sorted({int(fields[2],16) for fields in groups['PQWP3']})
    result['xtra_by_constellation']={name:dict(age_field_min=min(int(f[3+i]) for f in groups['PQWP3']),age_field_max=max(int(f[3+i]) for f in groups['PQWP3']),valid_sv_count_min=min(int(f[8+i],16).bit_count() for f in groups['PQWP3']),valid_sv_count_max=max(int(f[8+i],16).bit_count() for f in groups['PQWP3'])) for i,name in enumerate(constellations)}
if groups['PQWP4']:
    assert all(len(fields)>=7 for fields in groups['PQWP4'])
    result['ephemeris_valid_sv_counts']={name:sorted({int(f[2+i],16).bit_count() for f in groups['PQWP4']}) for i,name in enumerate(constellations)}
if groups['PQWP5']:
    assert all(len(fields)>=17 for fields in groups['PQWP5'])
    result['health_sv_counts']={name:{kind:sorted({int(f[offset+i],16).bit_count() for f in groups['PQWP5']}) for kind,offset in [('unknown',2),('good',7),('bad',12)]} for i,name in enumerate(constellations)}
(out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
