from pathlib import Path
import runpy,re,hashlib
root=Path('/mnt/e/RealmeX2Pro edk2');runpy.run_path(str(root/'reference/kernel122/ensure-rootfs-volume.py'))
k=Path('/home/cy122/pmos-samurai-rootfs122/camera123/kernel');own=Path('/home/cy122/workspace/realmeX2pro-AndroidR-droidspaces/source')
prefix=own/'drivers/media/platform/msm/camera_8150'
for name in ['cam_sensor_module/cam_csiphy/include/cam_csiphy_1_1_hwreg.h','cam_sensor_module/cam_csiphy/cam_csiphy_soc.c','cam_cpas/cpas_top/cam_cpastop_hw.c']:
    p=prefix/name;print('SOURCE',p.relative_to(own))
    if not p.exists():continue
    lines=p.read_text().splitlines();patterns=['3ph','settle','regulator','csi_vdd','175','101','100','hw_version','mipi-csi','v175'];selected=set()
    for i,l in enumerate(lines):
        if any(s in l.lower() for s in patterns):selected.update(range(max(0,i-5),min(len(lines),i+14)))
    print('\n'.join(f'{i+1}: {lines[i]}' for i in sorted(selected)))
for p in (k/'arch/arm64/boot/dts/qcom').glob('sm8150*'):
    if p.suffix not in ['.dts','.dtsi']:continue
    lines=p.read_text().splitlines()
    for i,l in enumerate(lines):
        if 'vreg_l3c' in l:print('MAINLINE_RAIL',p.name,'\n'.join(lines[max(0,i-6):i+12]))
for name in ['camss.c','camss-csiphy-3ph-1-0.c','camss-csid-gen2.c','camss-csiphy.h']:
    t=(k/'drivers/media/platform/qcom/camss'/name).read_text()
    if name=='camss.c':
        for a,b in [('s64 camss_get_link_freq','static int camss_of_parse_endpoint_node'),('static int camss_of_parse_endpoint_node','static int camss_of_parse_ports')]:
            if a in t:pos=t.index(a);end=t.find(b,pos+len(a));print('MAINLINE_FUNCTION',t[pos:end if end>=0 else pos+6000])
    elif name=='camss-csiphy-3ph-1-0.c':
        for a,b in [('static u8 csiphy_settle_cnt_calc','static void csiphy_gen1_config_lanes'),('static int csiphy_init','static void csiphy_release')]:
            if a in t:pos=t.index(a);end=t.find(b,pos+len(a));print('MAINLINE_FUNCTION',t[pos:end if end>=0 else pos+6000])
    elif name=='camss-csid-gen2.c':
        pos=t.index('static void __csid_configure_rx');print('MAINLINE_FUNCTION',t[pos:pos+2300])
    else:print('MAINLINE_HEADER',t[:5200])
print('ACTIVE_CAMERA_MAKEFILES')
for name in ['drivers/media/platform/msm/Makefile','drivers/media/platform/msm/camera_8150/Makefile','drivers/media/platform/msm/camera_8150/Kconfig']:
    p=own/name
    if p.exists():print(name,p.read_text()[:1800])
