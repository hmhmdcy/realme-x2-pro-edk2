from pathlib import Path
import runpy,json,hashlib,shutil
runpy.run_path('/mnt/e/RealmeX2Pro edk2/reference/kernel118/ensure-build-volume.py')
k=Path('/home/cy122/pmos-samurai-kernel118/kernel')
d=Path('/home/cy122/workspace/realmeX2pro-AndroidR-droidspaces/source')
out=Path('/mnt/e/edk2-samurai-out/kernel120');out.mkdir(exist_ok=True)
paths=[k/'arch/arm64/boot/dts/qcom/sm8150.dtsi',k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts',k/'Documentation/devicetree/bindings/i2c/qcom,i2c-cci.yaml',k/'drivers/i2c/busses/i2c-qcom-cci.c',d/'arch/arm64/boot/dts/19781/sm8150-camera.dtsi',d/'arch/arm64/boot/dts/19781/sm8150-camera-sensor-mtp.dtsi']
for p in paths:
    print('\nSOURCE',p.name)
    text=p.read_text();lines=text.splitlines()
    patterns=['cci','camcc','camss','qcom,cam-sensor','cam_v','gpio','cam-sensor']
    if p.name.endswith('yaml'):print(text)
    elif p.name=='i2c-qcom-cci.c':
        for i,line in enumerate(lines):
            if 'sm8150' in line or 'cci_v2_data' in line:print('\n'.join(lines[max(0,i-4):i+14]))
    else:
        hits=[i for i,line in enumerate(lines) if any(word in line.lower() for word in patterns)]
        selected=set()
        for i in hits:
            selected.update(range(max(0,i-3),min(len(lines),i+14)))
        print('\n'.join(f'{i+1}: {lines[i]}' for i in sorted(selected)))
print('BUILD_VOLUME_FREE_GIB',round(shutil.disk_usage(k).free/1024**3,2))
