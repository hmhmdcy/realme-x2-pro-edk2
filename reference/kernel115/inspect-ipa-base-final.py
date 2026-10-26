from pathlib import Path
import json,hashlib
base=Path('/home/cy122/workspace/realmeX2pro-AndroidR-droidspaces/source')
paths=[base/'drivers/platform/msm/ipa/ipa_v3/ipahal/ipahal_reg.c',base/'drivers/platform/msm/ipa/ipa_v3/ipahal/ipahal_reg.h',Path('/home/cy122/pmos-samurai-kernel114/kernel/drivers/net/ipa/ipa_mem.c')]
out=Path('/mnt/e/edk2-samurai-out/kernel115')
records=[]
for path in paths:
    lines=path.read_text().splitlines()
    patterns=['ipahal_get_reg_base','IPA_REG_BASE','SW_AREA_RAM_DIRECT_ACCESS','imem_addr','imem_size','imem_iova','smem_size']
    hits=[dict(line=i+1,text='\n'.join(lines[max(0,i-3):i+8])) for i,line in enumerate(lines) if any(p in line for p in patterns)]
    records.append(dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),hits=hits))
    print(path.name)
    for h in hits:
        if any(p in h['text'] for p in ['ipahal_get_reg_base','IPA_REG_BASE','imem_addr','imem_size']): print(h['line'],h['text'])
(out/'ipa-reg-and-memory-excerpts.json').write_text(json.dumps(records,indent=2)+'\n')
