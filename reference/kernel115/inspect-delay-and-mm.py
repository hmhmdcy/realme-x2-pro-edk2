from pathlib import Path
k=Path('/home/cy122/pmos-samurai-kernel115/kernel')
own=Path('/home/cy122/workspace/realmeX2pro-AndroidR-droidspaces/source/drivers/platform/msm/ipa/ipa_v3/ipahal')
for p,needles in [(k/'drivers/net/ipa/reg/ipa_reg-v4.1.c',['ENDP_INIT_CTRL','endp_init_ctrl']), (k/'drivers/net/ipa/reg/ipa_reg-v3.5.1.c',['endp_init_ctrl_fmask']), (own/'ipahal_reg.c',['ENDP_INIT_CTRL','endp_init_ctrl','ENDPOINT_DELAY'])]:
    lines=p.read_text().splitlines()
    print(p.name)
    for i,l in enumerate(lines):
        if any(n in l for n in needles): print(i+1,'\n'.join(lines[max(0,i-3):i+12]))
