"""Verify bounded layout facts against the fixed local OEM HAL, without running it."""
from pathlib import Path
import hashlib, json, struct

ROOT = Path(__file__).resolve().parent
hal = Path('/mnt/e/edk2-samurai-out/kernel281/camera.qcom.so-private').read_bytes()
sha = hashlib.sha256(hal).hexdigest()
assert sha == 'e2b1b9b6379507052464d9f9573c2a5a1b1cf37c43947b53645ddc8948a70dde'
offset = struct.unpack_from('<Q', hal, 32)[0]
size, count = struct.unpack_from('<HH', hal, 54)
loads = []
for i in range(count):
    kind, flags, start, address, physical, length, memory, align = struct.unpack_from('<IIQQQQQQ', hal, offset + i * size)
    if kind == 1:
        loads.append((address, start, length))

def read(address, length):
    for base, start, size in loads:
        if base <= address and address + length <= base + size:
            return hal[start + address - base:start + address - base + length]
    raise AssertionError(hex(address))

# Instruction fingerprints anchor the separately inspected symbol/pointer chains.
# They prove the recorded static layout, not silicon behavior or image quality.
instructions = {
    0x31bb8c: 0x5280ac01, 0x31bb90: 0x528000e2,  # Demux base0x560, seven words
    0x31c3e8: 0x331e01ae,  # calculated lens enable bit2
    0x377e3c: 0x331c6d0a, 0x377e44: 0x12003d4a, 0x377e4c: 0x2a085142,
    0x377e40: 0x120039e3, 0x377e54: 0x33103870, 0x377e70: 0x3310384d,
    0x378034: 0x52a89006, 0x378038: 0x528fffef, 0x378168: 0x5281ffe5,
    0x329fa4: 0x52814781, 0x329fa8: 0x52800162,  # FULL Y0xa3c, eleven words
    0x329fbc: 0x52814d01, 0x329fc0: 0x52800162,  # FULL C0xa68, eleven words
    0x32bbb4: 0xb943c98b, 0x32bbb8: 0x331d012b, 0x32bbbc: 0xb903c98b,
    0x2a9008: 0x910f227a, 0x2a98d0: 0x52800981, 0x2a98dc: 0xaa1a03e3,
    0x32b0a0: 0x32000606, 0x32b0c4: 0x3304056e,
    0x32b104: 0x330056c1, 0x32b118: 0x33003448, 0x32b140: 0x33103628,
    0x32b0d0: 0x121244ca, 0x32b10c: 0x120a2701, 0x32b0ac: 0x12020225,
    0x32b91c: 0xb940b778, 0x32b938: 0x3200070c,  # FULL C object, axes3
    0x32b980: 0x7901736c, 0x32b9a4: 0x33003d81,  # 16-bit H input/output
    0x32ba00: 0x79019b73, 0x32ba28: 0x33003e67,  # 16-bit V input/output
    0x32b944: 0x120202f0, 0x32b9c4: 0x1202000f,  # reserved pad bit30
    0x32b970: 0x330034d0, 0x32b9d8: 0x33005497,
    0x32e498: 0x7100101f, 0x32e4a0: 0x52800068,
}
for address, value in instructions.items():
    assert struct.unpack('<I', read(address, 4))[0] == value, hex(address)
report = dict(
    stage=287, hal_sha256=sha, static_only=True,
    checked_instruction_addresses=[hex(a) for a in instructions],
    demux=dict(base='0x560', words=7, enable='0x40 bit2', gains='unsigned15 Q10',
               black_fields=['15:4', '31:20'], unity_gain=1024,
               raw_bit_depth_does_not_prove_extra_gain=True),
    mnds=dict(full_y='0xa3c', full_c='0xa68', words_each=11, enable='0x4c bit3',
              y_size_bits=14, c_size_bits=16, phase_bits=22, interpolation_bits='29:28',
              phase_fraction_bits=14, pad_reserved_bit=30, dimension_minus_one=True,
              nv12_chroma_horizontal_and_vertical_divisor=2,
              single_axis_ratio_strictly_below=64, nv12_luma_ratio_strictly_below=32,
              single_stripe_only=True, crop_backend_not_implemented=True),
    fixed_reference_commit='9f17f1b568626b393e785b369c5dc94543774d7a',
    reference_receipt='../kernel286/next-normalization-sources-private.json (private)',
    no_oem_binary_execution=True, no_oem_implementation_copied=True,
    physical_alignment_color_order_and_isp_image_validation_pending=True,
    not_deployed=True,
)
(ROOT/'register-contract-validation.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
