"""Map real vmlinux symbols to the retained183 raw Image without rebuilding."""
from pathlib import Path
import hashlib
import json
import struct
import subprocess

R = Path(__file__).resolve().parent
K = Path('/home/cy122/pmos-samurai-kernel136/kernel')
P = Path('/mnt/e/edk2-samurai-out')
sha = lambda data: hashlib.sha256(data).hexdigest()
driver = (K / 'drivers/tty/serial/qcom_geni_serial.c').read_bytes()
core = (K / 'drivers/tty/serial/serial_core.c').read_bytes()
assert sha(driver) == '5bb9ba5ed694f1329eaf47d2de935bcfd0a405f63d5055a9b0ff1950890a527c'
assert sha(core) == '2053931aef71c605f85bb9c8406dd3f8f2c29ce353b76297425f8c013f2ffe0c'
# The exact base revision is checked against Git; no source refresh or checkout.
base = 'b0630f810366008d7afe9f83750f10f0c9492b9f'
assert subprocess.check_output(['git', 'show', base + ':drivers/tty/serial/qcom_geni_serial.c'], cwd=K) == driver
assert subprocess.check_output(['git', 'show', base + ':drivers/tty/serial/serial_core.c'], cwd=K) == core
image = (K / 'arch/arm64/boot/Image').read_bytes()
assert sha(image) == 'bfa72dd920c8376ceefc458fe7202a73ddb364b6727556471d70c8d0e7ade469'
assert image == (P / 'kernel183/Image-k183-offline-stream-private').read_bytes()
elf = (K / 'vmlinux').read_bytes()
assert elf[:6] == b'\x7fELF\x02\x01'
phoff = struct.unpack_from('<Q', elf, 32)[0]
phsize, phcount = struct.unpack_from('<HH', elf, 54)
loads = [struct.unpack_from('<IIQQQQQQ', elf, phoff + n * phsize) for n in range(phcount)]
loads = [p for p in loads if p[0] == 1]
names = ['_text', 'qcom_geni_serial_set_mctrl', 'qcom_geni_serial_set_termios']
symbols = {}
for line in subprocess.check_output(['aarch64-linux-gnu-nm', '-S', '--defined-only', str(K / 'vmlinux')], text=True).splitlines():
    fields = line.split()
    if fields[-1] in names:
        symbols[fields[-1]] = (int(fields[0], 16), int(fields[1], 16) if len(fields) == 4 else 0)
assert set(symbols) == set(names)
text_address = symbols['_text'][0]
results = {}
for name in names[1:]:
    address, size = symbols[name]
    matches = [p for p in loads if p[3] <= address and address + size <= p[3] + p[5]]
    assert len(matches) == 1
    load = matches[0]
    offset = load[2] + address - load[3]
    data = elf[offset:offset + size]
    assert data == image[address - text_address:address - text_address + size]
    targets = []
    for index in range(0, len(data), 4):
        instruction = struct.unpack_from('<I', data, index)[0]
        if instruction & 0xfc000000 == 0x94000000:
            immediate = instruction & 0x03ffffff
            if immediate & 0x02000000:
                immediate -= 0x04000000
            targets.append(address + index + immediate * 4)
    results[name] = dict(bytes=size, vmlinux_equals_retained_image=True,
                         direct_bl_set_mctrl=symbols['qcom_geni_serial_set_mctrl'][0] in targets)
assert results['qcom_geni_serial_set_mctrl']['bytes'] == 436
assert results['qcom_geni_serial_set_termios']['bytes'] == 964
assert not results['qcom_geni_serial_set_termios']['direct_bl_set_mctrl']
report = dict(stage=234, source_geni_sha256=sha(driver), source_core_sha256=sha(core),
              source_equals_base_commit=base, image183_sha256=sha(image), functions=results,
              deployed_image_link='233 verified logdump183 and unchanged Image183 boot payload',
              artifact_bytes_verified_not_live_instruction_probe=True,
              no_product_build_or_phone_operation=True)
(R / 'uart-artifact-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
