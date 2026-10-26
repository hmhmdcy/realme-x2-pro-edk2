from pathlib import Path
import runpy,re,json,hashlib
root=Path('/mnt/e/RealmeX2Pro edk2');runpy.run_path(str(root/'reference/kernel118/ensure-build-volume.py'))
own=Path('/home/cy122/workspace/realmeX2pro-AndroidR-droidspaces/source')
base=Path('/mnt/e/edk2-samurai-out/kernel115/camera-reference/aports/device/testing/linux-oneplus-hotdog-mainline616')
out=Path('/mnt/e/edk2-samurai-out/kernel123');out.mkdir(exist_ok=True)
for prefix in ['0066','0067','0074','0075','0076']:
    for p in base.glob(prefix+'*'):print('REFERENCE',p.name,p.read_text())
patterns=['vdda-phy','vdda-pll','cam_v','camss_phy','csiphy-supply','0x840','0x0860','0x0840','0x620']
for name in ['arch/arm64/boot/dts/19781/sm8150-camera.dtsi','arch/arm64/boot/dts/19781/sm8150-smmu.dtsi','arch/arm64/boot/dts/19781/sm8150-camera-sensor-mtp.dtsi']:
    p=own/name
    if not p.exists():continue
    lines=p.read_text().splitlines();selected=set()
    for i,l in enumerate(lines):
        if any(s in l.lower() for s in patterns):selected.update(range(max(0,i-5),min(len(lines),i+12)))
    print('NATIVE',p.name,'\n'.join(f'{i+1}: {lines[i]}' for i in sorted(selected)))
print('SMMU_FILES','\n'.join(str(p.relative_to(own)) for p in (own/'arch/arm64/boot/dts/19781').glob('*smmu*')))
