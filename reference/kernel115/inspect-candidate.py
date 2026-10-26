from pathlib import Path
import json
k = Path('/home/cy122/pmos-samurai-kernel114/kernel')
out = Path('/mnt/e/edk2-samurai-out/kernel115')
for rel, needles in {
    'drivers/net/ipa/data/ipa_data-v4.1.c':['imem_addr','core_clock_rate'],
    'arch/arm64/boot/dts/qcom/sm8150.dtsi':['ipa: ipa@'],
    'arch/arm64/boot/dts/qcom/sm8150-samurai.dts':['ipa_fw_mem','gsi_mem','&ipa'],
    'drivers/net/ipa/gsi_trans.c':['void gsi_trans_commit_wait'],
    'drivers/net/ipa/ipa_main.c':['ipa_firmware_load','IPA_LOADER_SELF'],
}.items():
    lines=(k/rel).read_text().splitlines()
    print(rel)
    for i,line in enumerate(lines):
        if any(n in line for n in needles):
            print(i+1, '\n'.join(lines[max(0,i-4):i+38]))
tree=json.loads(Path('/mnt/e/edk2-samurai-out/kernel114/primary-reference/tree.json').read_text())['tree']
print('Timeout patches:', [r['path'] for r in tree if 'patch' in r['path'] and any(n in r['path'].lower() for n in ['gsi','bound','timeout'])])
