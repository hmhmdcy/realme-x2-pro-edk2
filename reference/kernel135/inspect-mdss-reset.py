from pathlib import Path
import runpy
import hashlib
import json
r = Path('/mnt/e/RealmeX2Pro edk2')
runpy.run_path(str(r / 'reference/kernel134/ensure-build-volume.py'))
b = Path('/home/cy122/pmos-samurai-build134/usb134/kernel')
out = Path('/mnt/e/edk2-samurai-out/kernel135')
files = ['include/dt-bindings/clock/qcom,dispcc-sm8150.h',
         'drivers/clk/qcom/dispcc-sm8250.c', 'drivers/gpu/drm/msm/msm_mdss.c',
         'arch/arm64/boot/dts/qcom/sm8150.dtsi',
         'arch/arm64/boot/dts/qcom/sm8150-samurai.dts',
         'arch/arm64/boot/dts/qcom/.sm8150-samurai.dtb.cmd',
         'Documentation/devicetree/bindings/display/msm/mdss-common.yaml']
records = []
for f in files:
    p = b / f
    data = p.read_bytes()
    records.append(dict(path=f, bytes=len(data), sha256=hashlib.sha256(data).hexdigest()))
    dest = out / ('reset-source-' + p.name)
    if dest.exists():
        assert dest.read_bytes() == data
    else:
        dest.write_bytes(data)
    lines = data.decode().splitlines()
    indices = set()
    if f.endswith('.cmd'):
        print('FILE', f, '\n', '\n'.join(lines))
        continue
    for i, l in enumerate(lines):
        if any(x in l for x in ['MDSS_CORE_BCR', 'MDSS_RSCC_BCR', 'msm_mdss_reset',
                                'reset_control_', 'reset_map', 'mdss:', 'dispcc:',
                                'resets:', 'sm8150-dispcc', '&mdss {']):
            indices.update(range(max(0, i - 3), min(len(lines), i + 16)))
    print('FILE', f, '\n' + '\n'.join(f'{i+1}:{lines[i]}' for i in sorted(indices)))
(r / 'reference/kernel135/mdss-reset-source-snapshots.json').write_text(json.dumps(records, indent=2) + '\n')
