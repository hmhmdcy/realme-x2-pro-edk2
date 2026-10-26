from pathlib import Path
import runpy,os
r=Path('/mnt/e/RealmeX2Pro edk2');runpy.run_path(str(r/'reference/kernel118/ensure-build-volume.py'));runpy.run_path(str(r/'reference/kernel122/ensure-rootfs-volume.py'))
prefix=Path('/home/cy122/pmos-samurai-kernel118/camera120/schema-venv/lib')
for p in prefix.glob('python*/site-packages/dtschema/schemas/reserved-memory/reserved-memory.yaml'):print('INSTALLED_SCHEMA',p.read_text())
own=Path('/home/cy122/workspace/realmeX2pro-AndroidR-droidspaces/source/arch/arm64/boot/dts/19781/sm8150-camera.dtsi');t=own.read_text();i=t.index('msm_cam_smmu_ife');print('OWN_IFE_WINDOW',t[i:i+4200])
k=Path('/home/cy122/pmos-samurai-rootfs122/camera124/kernel');p=k/'drivers/media/platform/qcom/camss/camss.c';t=p.read_text();i=t.index('static int camss_probe');print('PROBE_AND_CLEANUP',t[i:i+8800])
p=k/'drivers/media/platform/qcom/camss/camss.h';t=p.read_text();i=t.index('struct camss {');print('CAMSS_STRUCT',t[i:i+2100])
