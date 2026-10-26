from pathlib import Path
import runpy
import subprocess
import hashlib
import json
import difflib
r = Path('/mnt/e/RealmeX2Pro edk2')
runpy.run_path(str(r / 'reference/kernel134/ensure-build-volume.py'))
b = Path('/home/cy122/pmos-samurai-build134/usb134/kernel')
out = Path('/mnt/e/edk2-samurai-out/kernel135')
ref = r / 'reference/kernel135'
assert not (out / 'DTB-k135-private').exists()
source = b / 'arch/arm64/boot/dts/qcom/sm8150-samurai.dts'
before = source.read_text()
old = '&mdss {\n\tstatus = "okay";\n};'
new = '&mdss {\n\tresets = <&dispcc DISP_CC_MDSS_CORE_BCR>;\n\tstatus = "okay";\n};'
assert before.count(old) == 1
after = before.replace(old, new)
(out / 'sm8150-samurai-reset.dts').write_text(after)
(ref / 'mdss-reset.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True), fromfile='a/arch/arm64/boot/dts/qcom/sm8150-samurai.dts', tofile='b/arch/arm64/boot/dts/qcom/sm8150-samurai.dts')))
pp = out / 'reset-preprocessed-private.dts'
commands = [
    ['gcc', '-E', '-nostdinc', '-I', './scripts/dtc/include-prefixes', '-I', 'arch/arm64/boot/dts/qcom', '-undef', '-D__DTS__', '-x', 'assembler-with-cpp', '-o', str(pp), str(out / 'sm8150-samurai-reset.dts')],
    ['./scripts/dtc/dtc', '-o', str(out / 'DTB-k135-private'), '-b', '0', '-iarch/arm64/boot/dts/qcom/', '-i./scripts/dtc/include-prefixes', '-Wno-unique_unit_address', '-Wno-unit_address_vs_reg', '-Wno-avoid_unnecessary_addr_size', '-Wno-alias_paths', '-Wno-interrupt_map', '-Wno-simple_bus_reg', str(pp)]
]
for i, command in enumerate(commands):
    p = subprocess.run(command, cwd=b, capture_output=True, timeout=90)
    (out / f'dtb-build-{i}-private.log').write_bytes(p.stdout + p.stderr)
    assert p.returncode == 0
assert source.read_text() == before
assert (b / 'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb').read_bytes() == (out.parent / 'kernel134/DTB-k134-private').read_bytes()
assert (b / 'arch/arm64/boot/Image').read_bytes() == (out.parent / 'kernel134/Image-k134-private').read_bytes()
print('K135_ISOLATED_RESET_DTB_COMPILED_ORIGINAL134_SOURCE_AND_ARTIFACTS_PRESERVED', flush=True)
