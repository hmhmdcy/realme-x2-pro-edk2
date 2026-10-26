from pathlib import Path
import runpy,json,subprocess
root=Path('/mnt/e/RealmeX2Pro edk2')
runpy.run_path(str(root/'reference/kernel118/ensure-build-volume.py'))
k=Path('/home/cy122/pmos-samurai-kernel118/camera121/kernel')
own=Path('/home/cy122/workspace/realmeX2pro-AndroidR-droidspaces/source')
private=Path('/mnt/e/edk2-samurai-out/kernel117/camera-dt-reference')
print('REFERENCE_PATCHES')
for p in sorted(private.glob('*')):print(p.name)
paths=[k/'drivers/media/platform/qcom/camss/camss-csiphy-3ph-1-0.c',k/'drivers/media/platform/qcom/camss/camss.c',k/'Documentation/devicetree/bindings/media/qcom,sm8250-camss.yaml',own/'arch/arm64/boot/dts/19781/sm8150-camera.dtsi']
for p in paths:
    print('SOURCE',p.name)
    if not p.exists():continue
    lines=p.read_text().splitlines();selected=set()
    patterns=['sm8150','sc8280xp','cphy','3phase','three_phase','qos','interconnect','iommu','reg =','reg-names','interrupts =','interrupt-names','clock-names','phy-mode','data-lanes']
    for i,l in enumerate(lines):
        if any(s in l.lower() for s in patterns):selected.update(range(max(0,i-3),min(len(lines),i+16)))
    print('\n'.join(f'{i+1}: {lines[i]}' for i in sorted(selected)))
for p in sorted(private.glob('0056*')):print('DT_REFERENCE',p.read_text())
