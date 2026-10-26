from pathlib import Path
import hashlib,json,re

base=Path('/home/cy122/workspace/realmeX2pro-AndroidR-droidspaces/source')
paths=[base/'arch/arm64/boot/dts/19781/sm8150.dtsi',base/'drivers/platform/msm/ipa/ipa_v3/ipa.c',base/'drivers/platform/msm/ipa/ipa_v3/ipa_utils.c',base/'drivers/platform/msm/ipa/ipa_v3/ipa_uc.c']
directory=base/'drivers/platform/msm/ipa'
patterns=['REG_BASE_OFST','reg_base_offset','ctrl->ipa_reg_base','ipa_reg_base','IPA_REG_BASE','IMEM','imem','ipa_4_1_mem_part']
out=Path('/mnt/e/edk2-samurai-out/kernel115');out.mkdir(exist_ok=True)
records=[]
for path in directory.rglob('*'):
    if path.suffix not in ['.c','.h']:continue
    text=path.read_text(errors='replace')
    lines=text.splitlines()
    hits=[i for i,line in enumerate(lines) if any(p in line for p in patterns)]
    if not hits:continue
    records.append(dict(path=str(path.relative_to(base)),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),hits=[dict(line=i+1,text='\n'.join(lines[max(0,i-2):i+4])) for i in hits]))
(out/'ipa-own-source-excerpts.json').write_text(json.dumps(records,indent=2)+'\n')
for record in records:
    if any('BASE_OFST' in h['text'] or 'reg_base_offset' in h['text'] or 'imem' in h['text'].lower() for h in record['hits']):
        print(record['path'])
        for h in record['hits']:
            if any(p in h['text'] for p in ['BASE_OFST','reg_base_offset','IMEM','imem']):print(h['line'],h['text'])
