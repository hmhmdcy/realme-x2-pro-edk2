"""Pure host audit of C source expressions against retained factory A64 code.

Does not compile or execute the driver, OEM ELF, SDK, or any phone command.
"""
from pathlib import Path
import ast
import hashlib
import importlib.util
import json
import re
import struct
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('wire_storage449', HERE.parent / 'kernel449/storage.py')
storage = importlib.util.module_from_spec(spec); spec.loader.exec_module(storage)
storage.mount.mounted_build()
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel453')
PRIVATE.mkdir(exist_ok=True)
retained = PRIVATE.parent / 'kernel450/lens-scope'
decoded = json.loads((retained / 'decoded-private.json').read_text())
source = (HERE / 'bu64253.c').read_text()
binary = (PRIVATE.parent / 'kernel281/camera.qcom.so-private').read_bytes()
assert hashlib.sha256(binary).hexdigest() == 'e2b1b9b6379507052464d9f9573c2a5a1b1cf37c43947b53645ddc8948a70dde'


def va(address, size):
    offset = struct.unpack_from('<Q', binary, 32)[0]
    entry_size, count = struct.unpack_from('<HH', binary, 54)
    for i in range(count):
        typ, flags, file_offset, vaddr, paddr, filesz, memsz, align = struct.unpack_from('<II6Q', binary, offset + i * entry_size)
        if typ == 1 and vaddr <= address and address + size <= vaddr + filesz:
            return binary[file_offset + address - vaddr:file_offset + address - vaddr + size]
    raise AssertionError(hex(address))


instructions = {pc: struct.unpack('<I', va(pc, 4))[0] for pc in [0x41e0a0, 0x41e0a4, 0x41e0d0, 0x41e17c, 0x41e184, 0x41e188]}
assert instructions == {0x41e0a0: 0x52801890, 0x41e0a4: 0x12001d91, 0x41e0d0: 0x33082590,
                        0x41e17c: 0x7103febf, 0x41e184: 0x1a950215, 0x41e188: 0x1a9b023b}
# The first dispatch-table entry is selected by operation WRITE_DAC_VALUE == 1.
assert va(0xd3cb2, 1) == bytes([(0x41e158 - 0x41e0d8) // 4])


def logical_mask(word):
    n, immr, imms = word >> 22 & 1, word >> 16 & 63, word >> 10 & 63
    length = (n << 6 | (~imms & 63)).bit_length() - 1
    width = 1 << length; levels = width - 1
    s, r = imms & levels, immr & levels
    assert width <= 32 and s != levels
    element = (1 << (s + 1)) - 1
    element = ((element >> r) | (element << (width - r))) & ((1 << width) - 1)
    return sum(element << i for i in range(0, 32, width))


def factory_command(position):
    # Decode the actual MOVZ/AND/BFM fields; no native/emulated OEM execution.
    mov = instructions[0x41e0a0]; and_ = instructions[0x41e0a4]; bfm = instructions[0x41e0d0]
    assert mov & 31 == 16 and and_ & 31 == 17 and and_ >> 5 & 31 == 12
    assert bfm & 31 == 16 and bfm >> 5 & 31 == 12
    high = (mov >> 5 & 0xffff) << ((mov >> 21 & 3) * 16)
    low = position & logical_mask(and_)
    immr, imms = bfm >> 16 & 31, bfm >> 10 & 31
    assert imms >= immr
    mask = (1 << (imms - immr + 1)) - 1
    high = (high & ~mask) | (position >> immr & mask)
    # CMP 0xff is true for both independently decoded module register records.
    return bytes([high, low])


assignments = dict(re.findall(r'data\[(\d)\]\s*=\s*([^;]+);', source))
assert set(assignments) == {'0', '1'}
allowed = (ast.Expression, ast.BinOp, ast.BitAnd, ast.BitOr, ast.RShift, ast.Constant, ast.Name, ast.Load)
expressions = []
for index in ['0', '1']:
    tree = ast.parse(assignments[index], mode='eval')
    assert all(isinstance(n, allowed) for n in ast.walk(tree))
    assert all(n.id == 'position' for n in ast.walk(tree) if isinstance(n, ast.Name))
    expressions.append(compile(tree, '<draft C arithmetic expression>', 'eval'))
for position in range(1024):
    candidate = bytes(eval(expr, {'__builtins__': {}}, {'position': position}) for expr in expressions)
    assert candidate == factory_command(position), position
assert 'if (position > BU64253_MAX_FOCUS)' in source
assert re.search(r'BU64253_MAX_FOCUS\s+1023', source)
assert re.search(r'V4L2_CID_FOCUS_ABSOLUTE,\s*0,\s*BU64253_MAX_FOCUS,\s*1,\s*0', source)


def accept_file(blob):
    if blob is None:
        return False
    if len(blob) != 20 or blob[:8] != b'BU53\x01\x03\x00\x00':
        return False
    entries = [struct.unpack_from('<BBH', blob, 8 + i * 4) for i in range(3)]
    return (entries[0][0] == 0xd0 and entries[0][1] in [0x71, 0x78] and entries[0][2] == 5 and
            entries[1] == (0xc8, 1, 100) and entries[2] == (0xf0, 0x80, 10))


fw_records = []
private_records = []
for module, filename in [('sunny_imx319', 'imx319-bu64253-init.bin'), ('qtech_s5k3m5sx-current326', 's5k3m5sx-bu64253-init.bin')]:
    row = next(r for r in decoded['actuators'] if r['module'] == module)
    xml_path = next((retained / ('parser-' + module) / 'xml').rglob('actuatorDriver.xml'))
    xml = ET.parse(xml_path).getroot()
    init = [(int(x.findtext('registerAddr')), int(x.findtext('registerData')), int(x.findtext('delayUs'))) for x in xml.findall('initSettings/regSetting')]
    assert init == [(r['address'], r['values'][0], r['delays_us'][0]) for r in row['init']]
    assert row['position'] == [[1, 1, 255, 0, 1, 1, 0, 0, 0]]
    blob = b'BU53\x01\x03\x00\x00' + b''.join(struct.pack('<BBH', *r) for r in init)
    assert accept_file(blob)
    (PRIVATE / filename).write_bytes(blob)
    fw_records.append(dict(module=module, filename=filename, bytes=len(blob), sha256=hashlib.sha256(blob).hexdigest(),
                           source_sha256=row['source_sha256'], independent_xml_sha256=hashlib.sha256(xml_path.read_bytes()).hexdigest()))
    private_records.append(dict(**fw_records[-1], initial_code=row['initial_code'], regions=row['regions']))

sample = (PRIVATE / fw_records[0]['filename']).read_bytes()
negative = [None, b'', sample[:-1], sample + bytes([0])]
for index, value in [(0, 0), (4, 2), (5, 2), (6, 1), (7, 1), (8, 0xe0), (9, 0), (10, 0), (12, 0xd0), (13, 0), (14, 0), (16, 0xc8), (17, 0), (18, 0)]:
    bad = bytearray(sample); bad[index] = value; negative.append(bytes(bad))
assert all(not accept_file(blob) for blob in negative)
# These are static ordering checks, not execution of kernel/PM error paths.
probe = source[source.index('static int bu64253_probe'):source.index('static void bu64253_remove')]
assert probe.index('bu64253_load_init(dev, lens)') < probe.index('v4l2_async_register_subdev')
loader = source[source.index('static int bu64253_load_init'):source.index('static int bu64253_set_ctrl')]
assert 'i2c_master_send' not in loader and 'regulator_enable' not in loader
resume = source[source.index('static int bu64253_runtime_resume'):source.index('static int bu64253_runtime_suspend')]
assert resume.index('if (!lens->init_valid)') < resume.index('regulator_enable') < resume.index('bu64253_write')
assert 'usleep_range(BU64253_START_US' in resume and re.search(r'BU64253_START_US\s+10000', source)
assert '0x84' not in source and '0xe0' not in source and 'pm_runtime_get_if_in_use' in source

private = dict(firmware=private_records, instruction_words={hex(k):hex(v) for k,v in instructions.items()},
               examples={str(n):factory_command(n).hex() for n in [0, 1, 255, 256, 511, 512, 1023]})
(PRIVATE / 'wire-contract-private.json').write_text(json.dumps(private, indent=2) + '\n')
report = dict(stage=453, scope='draft arithmetic expressions and private init-file host contract',
              factory_hal_sha256=hashlib.sha256(binary).hexdigest(), factory_move_focus='0x41dc40..0x41e638',
              exact_factory_instruction_words_and_dispatch_verified=True, all_1024_valid_dac_encodings_match=True,
              private_firmware=fw_records, invalid_or_missing_format_cases=len(negative), static_fail_before_write_order_checked=True,
              initial_target_not_written_merely_on_open=True, kernel_pm_framework_tested=False,
              c_driver_compiled_by_this_check=False, dts_binding_compiled_or_schema_checked=False,
              hardware_identity_or_focus_verified=False, sdk_or_phone_accessed=False,
              draft_source_sha256=hashlib.sha256(source.encode()).hexdigest(), passed=True)
(HERE / 'wire-contract-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
