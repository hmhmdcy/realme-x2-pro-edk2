from pathlib import Path
import runpy,re
root=Path('/mnt/e/RealmeX2Pro edk2')
runpy.run_path(str(root/'reference/kernel122/ensure-rootfs-volume.py'))
k=Path('/home/cy122/pmos-samurai-rootfs122/camera123/kernel')
own=Path('/home/cy122/workspace/realmeX2pro-AndroidR-droidspaces/source')
base=Path('/mnt/e/edk2-samurai-out/kernel115/camera-reference/aports/device/testing/linux-oneplus-hotdog-mainline616')
for p in base.glob('0089*'):print('REFERENCE_CPHY',p.read_text())
print('NATIVE_PHY_HEADERS','\n'.join(str(p.relative_to(own)) for p in (own/'drivers/media/platform').rglob('cam_csiphy_1_1_hwreg.h')))
print('NATIVE_CPAS_HEADERS','\n'.join(str(p.relative_to(own)) for p in (own/'drivers/media/platform').rglob('*175*')))
targets=[(k/'drivers/media/platform/qcom/camss/camss-csiphy.c',['regulator','set_stream','stream']), (k/'drivers/media/platform/qcom/camss/camss-csid.c',['regulator','set_stream','phy']), (k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts',['l3c','ldoc3','ldo3','vreg_l3','l3a','ldoa3']), (own/'drivers/media/platform/msm/camera/cam_sensor_module/cam_csiphy/cam_csiphy_core.c',['mipi','csi_vdd','regulator']), (own/'drivers/media/platform/msm/camera/cam_cpas/cam_cpas_hw.c',['175','101','100','hw_version'])]
for p,patterns in targets:
    print('SOURCE',p)
    if not p.exists():continue
    lines=p.read_text().splitlines();selected=set()
    for i,l in enumerate(lines):
        if any(s in l for s in patterns):selected.update(range(max(0,i-5),min(len(lines),i+12)))
    print('\n'.join(f'{i+1}: {lines[i]}' for i in sorted(selected)))
print('CPAS_MAIN_FILES','\n'.join(str(p.relative_to(own)) for p in (own/'drivers/media/platform').rglob('cam_cpas_hw.c')))
