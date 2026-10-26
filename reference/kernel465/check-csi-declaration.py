"""Replay the retained HAL's small CSI packet preparation fragment offline.

The source values and all provider memory are explicit; this is not an Android
run, a sensor PLL model, or a CSIPHY hardware frequency measurement.
"""
from pathlib import Path
import hashlib
import json
import struct
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, '/home/cy122/.local/lib/python3.14/site-packages')
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm64_const import *

HERE = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel465')
HAL = PRIVATE.parent / 'kernel281/camera.qcom.so-private'
HAL_SHA = 'e2b1b9b6379507052464d9f9573c2a5a1b1cf37c43947b53645ddc8948a70dde'
raw = HAL.read_bytes()
assert hashlib.sha256(raw).hexdigest() == HAL_SHA
phoff = struct.unpack_from('<Q', raw, 32)[0]
stride, count = struct.unpack_from('<HH', raw, 54)
segments = [struct.unpack_from('<II6Q', raw, phoff + i * stride) for i in range(count)]

def at(address, size):
    segment = next(s for s in segments if s[0] == 1 and s[3] <= address and address + size <= s[3] + s[5])
    offset = segment[2] + address - segment[3]
    return raw[offset:offset + size]

START, END = 0x4423c0, 0x4423f4
fragment = at(START, END - START)
decoded = list(Cs(CS_ARCH_ARM64, CS_MODE_ARM).disasm(fragment, START))
expected = [
    ('ldp', 'w28, w21, [x5, #0x50]'), ('ldr', 'w12, [x5, #0x40]'),
    ('ldr', 'w13, [x5, #0x28]'), ('sturb', 'w21, [x29, #-0x9c]'),
    ('mul', 'x21, x28, x26'), ('lsl', 'w2, w7, w12'),
    ('sub', 'w3, w2, #1'), ('csel', 'w27, w3, w10, eq'),
    ('sturb', 'w12, [x29, #-0x9a]'), ('sturb', 'w11, [x29, #-0x99]'),
    ('stp', 'x21, x13, [x29, #-0x98]'), ('sturh', 'w27, [x29, #-0xa0]'),
    ('sub', 'x2, x29, #0xa0'),
]
assert [(i.mnemonic, i.op_str) for i in decoded] == expected
following = next(Cs(CS_ARCH_ARM64, CS_MODE_ARM).disasm(at(END, 4), END))
assert (following.mnemonic, following.op_str) == ('bl', '#0x424820')

analysis = json.loads((PRIVATE / 'tele-mode-analysis-private.json').read_text())
rows = []
for label, clock, settle, lanes in [
    ('stock-mode2', analysis['modes']['b'][2]['output_pixel_clock'], 14, 4),
    ('stock-mode3', analysis['modes']['b'][3]['output_pixel_clock'], 14, 4),
    ('separate-declared-clock-sentinel', 123456789, 14, 4),
]:
    machine = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
    machine.mem_map(0x442000, 4096)
    machine.mem_write(START, fragment)
    resolution, frame = 0x1000000, 0x2001000
    machine.mem_map(resolution, 4096)
    machine.mem_map(frame - 4096, 8192)
    machine.mem_write(resolution + 0x28, struct.pack('<I', clock))
    machine.mem_write(resolution + 0x40, struct.pack('<I', lanes))
    machine.mem_write(resolution + 0x50, struct.pack('<II', settle, 0))
    for register, value in [(UC_ARM64_REG_X5, resolution), (UC_ARM64_REG_X29, frame),
                            (UC_ARM64_REG_X26, 200000000), (UC_ARM64_REG_X7, 2),
                            (UC_ARM64_REG_X10, 24), (UC_ARM64_REG_X11, 0),
                            (UC_ARM64_REG_NZCV, 0x40000000)]:
        machine.reg_write(register, value)
    instructions = []
    machine.hook_add(UC_HOOK_CODE, lambda u, address, size, unused: instructions.append(address))
    machine.emu_start(START, END, count=30)
    packet = bytes(machine.mem_read(frame - 0xa0, 24))
    mask = struct.unpack_from('<H', packet)[0]
    settle_output, declared_output = struct.unpack_from('<QQ', packet, 8)
    assert instructions == list(range(START, END, 4))
    assert machine.reg_read(UC_ARM64_REG_X2) == frame - 0xa0
    assert (mask, packet[4], packet[6], packet[7]) == (31, 0, 4, 0)
    assert settle_output == settle * 200000000 and declared_output == clock
    rows.append(dict(case=label, instructions=len(instructions), resolution_offset_0x28=clock,
                     packet_offset_16=declared_output, values_identical=True,
                     full_android_runtime_or_physical_rate_measured=False))

(PRIVATE / 'csi-packet-fragment-private.asm').write_text('\n'.join(f'{i.address:08x}: {i.mnemonic} {i.op_str}' for i in decoded) + '\n')
report = dict(stage=465, hal_sha256=HAL_SHA, function='CamX::SensorNode::CreateSensorSubmodules()',
              function_start='0x441148', function_bytes=0x3a68,
              fragment_start=hex(START), fragment_end_exclusive=hex(END),
              fragment_sha256=hashlib.sha256(fragment).hexdigest(), following_call='CamX::CSIPHYSubmodule::Configure(int, CSLSensorCSIPHYInfo const*)@0x424820',
              cases=rows, actual_original_instructions=sum(r['instructions'] for r in rows),
              declared_slot_copy_not_lane_rate_conversion=True,
              source_field_name_proven_by_full_original_structure_parser=False,
              stock_android_runtime_metadata_not_observed=True,
              op_pll_register_0x0312_semantics_proven=False,
              linux_link_frequency_proven=False,
              no_hal_external_function_or_hardware_executed=True, phone_accessed=False, passed=True)
(HERE / 'csi-declaration-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
