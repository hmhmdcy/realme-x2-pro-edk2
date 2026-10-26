from pathlib import Path
import gzip, re, urllib.request

out=Path('/mnt/e/edk2-samurai-out/kernel75')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel75')
base='https://raw.githubusercontent.com/realme-kernel-opensource/realmeX2Pro-kernel-source/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6/drivers/gpu/drm/msm/'
for relative in ('sde/sde_hw_dsc.c','sde/sde_encoder.c','sde/sde_hw_pingpong.c','dsi-staging/dsi_ctrl_hw_2_0.c'):
    name=relative.rsplit('/',1)[-1]
    p=out/('stock-'+name)
    if not p.exists():
        p.write_bytes(urllib.request.urlopen(base+relative,timeout=30).read())
    src=p.read_text().splitlines()
    print(name)
    if name=='sde_hw_dsc.c':
        print('\n'.join(src[40:167]))
    else:
        needles=r'dsc.*(initial|pic_width)|pic_width.*dsc|soft_slice_per_enc|DSC_MODE|enc_ip_w|intf_ip_w|dsc.*(merge|setup)|setup.*dsc'
        indices=[i for i,s in enumerate(src) if re.search(needles,s,re.I)]
        wanted=set()
        for i in indices:
            wanted.update(range(max(0,i-4),min(len(src),i+6)))
        print('\n'.join(f'{i+1}: {src[i]}' for i in sorted(wanted)))

for name in ('static-white-kms','flower-kms'):
    p=out/(name+'.gz')
    src=gzip.decompress(p.read_bytes()).decode()
    (out/(name+'.txt')).write_text(src)
    print(name)
    sections=re.split(r'(={5,}[^\n]+=+)',src)
    for i in range(1,len(sections),2):
        if re.search(r'dsi0_ctrl|dsc_[01]|mdp|merge',sections[i]):
            lines=sections[i+1].splitlines()
            print(sections[i], '\n'.join(lines[:12]))
