from pathlib import Path
import runpy
r=Path('/mnt/e/RealmeX2Pro edk2');runpy.run_path(str(r/'reference/kernel122/ensure-rootfs-volume.py'));k=Path('/home/cy122/pmos-samurai-rootfs122/camera125/kernel');t=(k/'arch/arm64/boot/dts/qcom/sm8150.dtsi').read_text();a=t.index('\t\tcamss: camss@');b=t.index('\t\tcamcc:',a);print(t[a:b]);print('RESERVED_MEMORY_MARKER',[l for l in t.splitlines() if 'reserved-memory' in l])
