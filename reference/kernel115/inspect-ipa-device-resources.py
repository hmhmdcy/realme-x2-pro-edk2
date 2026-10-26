from pathlib import Path
import json,hashlib
base=Path('/home/cy122/workspace/realmeX2pro-AndroidR-droidspaces/source')
out=Path('/mnt/e/edk2-samurai-out/kernel115')
files=['arch/arm64/boot/dts/19781/sm8150.dtsi','arch/arm64/boot/dts/qcom/sm8150.dtsi','drivers/platform/msm/ipa/ipa_v3/ipahal/ipahal_reg.c']
records=[]
for rel in files:
    path=base/rel;lines=path.read_text().splitlines()
    hits=[]
    for i,line in enumerate(lines):
        if any(p in line for p in ['ipa_smmu_ap:','qcom,ipa_fws','ipa_hw:','ipahal_get_reg_base','IPA_SW_AREA_RAM_DIRECT_ACCESS_n =','146BD','146bd','IPA_HW_v4_1']):
            hits.append(dict(line=i+1,text='\n'.join(lines[max(0,i-2):i+24])))
    records.append(dict(path=rel,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),hits=hits))
    print(rel)
    for h in hits:
        if 'IPA_HW_v4_1' not in h['text']: print(h['line'],h['text'])
(out/'own-ipa-device-resources.json').write_text(json.dumps(records,indent=2)+'\n')
