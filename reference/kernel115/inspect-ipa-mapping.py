from pathlib import Path
import hashlib,json
base=Path('/home/cy122/workspace/realmeX2pro-AndroidR-droidspaces/source')
patterns=['reg_base_ofst','ipahal_init(', '0x00040000','0x146a8000','0x146A8000','IPA_HW_v4_1','ipa_4_1_mem_part']
records=[]
for path in (base/'drivers/platform/msm/ipa/ipa_v3').rglob('*'):
    if path.suffix not in ['.c','.h'] or 'dump' in path.parts: continue
    lines=path.read_text(errors='replace').splitlines()
    hits=[dict(line=i+1,text='\n'.join(lines[max(0,i-3):i+6])) for i,line in enumerate(lines) if any(p in line for p in patterns)]
    if hits:records.append(dict(path=str(path.relative_to(base)),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),hits=hits))
out=Path('/mnt/e/edk2-samurai-out/kernel115')
(out/'ipa-mapping-excerpts.json').write_text(json.dumps(records,indent=2)+'\n')
for r in records:
    if any('reg_base_ofst' in h['text'] or 'ipahal_init(' in h['text'] for h in r['hits']):
        print(r['path'])
        for h in r['hits']:
            if any(p in h['text'] for p in ['reg_base_ofst','ipahal_init(','0x00040000']):print(h['line'],h['text'])
print('FILES_WITH_VERSION_OR_MAPPING_EVIDENCE',len(records))
