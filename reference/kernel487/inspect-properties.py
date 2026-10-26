"""Bounded offline inspection of retained handset metadata and HAL fragments."""
from pathlib import Path
import hashlib
import importlib.util
import json
import math
import struct
import sys
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out')
OUT = PRIVATE / 'kernel487'
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()


def descriptor(path):
    data = path.read_bytes()
    assert data.startswith(b'QTI Chromatix Header\0') and b'Parameter Parser V1.3.2 ' in data[:0x98]
    table, count = struct.unpack_from('<II', data, 0x98)
    sections = [struct.unpack_from('<QQQ', data, table + i * 24) for i in range(count)]
    assert [s[0] for s in sections] == [0, 1, 2]
    _, symbols, size = sections[0]
    _, payload, payload_size = sections[1]
    assert symbols + size <= len(data) and payload + payload_size <= len(data) and size % 72 == 0
    entries = {}
    for at in range(symbols, symbols + size, 72):
        uid = struct.unpack_from('<Q', data, at)[0]
        name = data[at + 8:at + 40].split(b'\0')[0].decode('ascii')
        relative, length = struct.unpack_from('<QQ', data, at + 56)
        assert relative + length <= payload_size and uid not in entries
        entries[uid] = (name, data[payload + relative:payload + relative + length])
    roots = [value for name, value in entries.values() if name == 'sensorDriverData']
    assert len(roots) == 1 and len(roots[0]) == 816
    root = roots[0]
    q = struct.unpack('<102Q', root)
    name, value = entries[q[4]]
    assert name == 'sensorName'
    sensor = value[:q[3]].rstrip(b'\0').decode('ascii')
    property_values = struct.unpack_from('<ddQ', root, 92 * 8)
    angles = {name: struct.unpack('<d', value)[0] for name, value in entries.values()
              if name in ['maxRollDegree', 'maxPitchDegree', 'maxYawDegree'] and len(value) == 8}
    return root, dict(path=str(path), sha256=sha(path), sensor=sensor,
                     serialized_tail_qword=92, pixel_size_um=property_values[0],
                     crop_factor=property_values[1], sensing_method=property_values[2],
                     named_oem_mount_angles=angles)


def main():
    spec = importlib.util.spec_from_file_location('guard487', HERE.parent / 'kernel284/storage.py')
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    guard.mounted_build()
    OUT.mkdir(exist_ok=True)
    sys.path.insert(0, '/home/cy122/.local/lib/python3.14/site-packages')
    from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
    from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE
    from unicorn.arm64_const import (UC_ARM64_REG_X3, UC_ARM64_REG_X12, UC_ARM64_REG_X13,
        UC_ARM64_REG_X19, UC_ARM64_REG_X20, UC_ARM64_REG_X24, UC_ARM64_REG_X27,
        UC_ARM64_REG_X28, UC_ARM64_REG_X29, UC_ARM64_REG_X30, UC_ARM64_REG_SP, UC_ARM64_REG_D19)
    hal = PRIVATE / 'kernel281/camera.qcom.so-private'
    assert sha(hal) == 'e2b1b9b6379507052464d9f9573c2a5a1b1cf37c43947b53645ddc8948a70dde'
    raw = hal.read_bytes()
    ph = struct.unpack_from('<Q', raw, 32)[0]
    stride, count = struct.unpack_from('<HH', raw, 54)
    segments = [struct.unpack_from('<II6Q', raw, ph + i * stride) for i in range(count)]

    def at(address, length):
        seg = next(s for s in segments if s[0] == 1 and s[3] <= address and address + length <= s[3] + s[5])
        offset = seg[2] + address - seg[3]
        return raw[offset:offset + length]

    paths = sorted((PRIVATE / 'kernel115/vendor-camera-bins').glob('com.qti.sensormodule.*.bin'))
    assert len(paths) == 6
    paths += [PRIVATE / 'kernel326/qtech_s5k3m5sx-description-private.bin',
              PRIVATE / 'kernel326/sunny_imx471-description-private.bin']
    descriptors = [descriptor(path) for path in paths]
    wanted = {'s5kgw1': 0.8, 'imx319': 1.4, 's5k3m5sx': 1.0, 'imx471': 1.0}
    assert all(metadata['pixel_size_um'] == wanted[metadata['sensor']] for root, metadata in descriptors)
    sentinel = bytearray(816)
    struct.pack_into('<ddQ', sentinel, 736, 2.75, 7.125, 3)
    cases = []
    for root, metadata in descriptors + [(bytes(sentinel), dict(sensor='distinct-sentinel', pixel_size_um=2.75, crop_factor=7.125, sensing_method=3))]:
        u = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
        u.mem_map(0x190000, 0x2000)
        u.mem_write(0x190000, at(0x190000, 0x2000))
        u.mem_map(0x1000000, 0x10000)
        B, C, PTR, L, D, S = range(0x1000000, 0x1006000, 0x1000)
        u.mem_write(B, root)
        u.mem_write(C, struct.pack('<Q', 736))
        u.mem_write(PTR, struct.pack('<Q', B))
        u.mem_write(L, struct.pack('<I', 816))
        u.mem_write(S + 0x100 - 24, struct.pack('<Q', 8))
        for register, value in [(UC_ARM64_REG_X3, 736), (UC_ARM64_REG_X12, B), (UC_ARM64_REG_X19, 8),
                (UC_ARM64_REG_X20, PTR), (UC_ARM64_REG_X24, D), (UC_ARM64_REG_X27, L),
                (UC_ARM64_REG_X28, C), (UC_ARM64_REG_X29, S + 0x100)]:
            u.reg_write(register, value)
        pcs = []
        u.hook_add(UC_HOOK_CODE, lambda machine, address, size, unused: pcs.append(address))
        u.emu_start(0x191114, 0x19120c, count=500)
        actual = struct.unpack('<ddI', u.mem_read(D + 600, 20))
        assert actual == (metadata['pixel_size_um'], metadata['crop_factor'], metadata['sensing_method'])
        assert struct.unpack('<Q', u.mem_read(C, 8))[0] == 760 and len(pcs) < 100
        parser_instructions = len(pcs)
        u.mem_map(0x4f4000, 0x2000)
        u.mem_write(0x4f4000, at(0x4f4000, 0x2000))
        cap, stack, dimensions = 0x1008000, 0x100a000, 0x100c000
        # Deliberately distinct provider axes, not a claimed handset array size.
        u.mem_write(D + 0x230, struct.pack('<6I', 1000, 2000, 0, 0, 0, 0))
        u.mem_write(stack + 0x20, struct.pack('<Q', dimensions))
        u.reg_write(UC_ARM64_REG_SP, stack)
        u.reg_write(UC_ARM64_REG_X13, D)
        u.reg_write(UC_ARM64_REG_X30, cap)
        u.emu_start(0x4f4e08, 0x4f4e84, count=100)
        pixel, width, height = struct.unpack('<3f', u.mem_read(cap + 0x2424, 12))
        assert math.isclose(pixel, actual[0], rel_tol=1e-6)
        assert math.isclose(width, actual[0], rel_tol=1e-6) and math.isclose(height, actual[0] * 2, rel_tol=1e-6)
        assert struct.unpack('<d', struct.pack('<Q', u.reg_read(UC_ARM64_REG_D19)))[0] == 1000.0
        assert len(pcs) - parser_instructions == 31
        assert all(0x190f08 <= pc < 0x19120c for pc in pcs[:parser_instructions])
        assert pcs[parser_instructions:] == list(range(0x4f4e08, 0x4f4e84, 4))
        cases.append(dict(**metadata, native_offsets=[600, 608, 616],
            root_parser_instructions=parser_instructions, consumer_instructions=31,
            fixture_axes_pixels=[1000, 2000], native_pixel_size_float=pixel,
            native_physical_size_mm=[width, height], divisor=1000.0, external_provider_called=False))
    schema = PRIVATE / 'kernel117/CamxChi/chi-cdk/api/sensor/camxsensordriver.xsd'
    ns = {'x': 'http://www.w3.org/2001/XMLSchema'}
    node = ET.parse(schema).find(".//x:complexType[@name='SensorProperty']", ns)
    fields = node.findall('x:sequence/x:element', ns)
    assert [(f.attrib['name'], f.attrib['type']) for f in fields] == [('pixelSize', 'xs:double'), ('cropFactor', 'xs:double'), ('sensingMethod', 'SensingMethod')]
    assert 'micro meters' in ''.join(fields[0].itertext())
    source = PRIVATE / 'kernel465/sources/camximagesensordata.cpp'
    text = source.read_text()
    assert 'physicalSensorSize.width = ImageSensorUtils::CalculatePhysicalSensorWidth(m_pSensorData)' in text
    assert 'physicalSensorSize.height = ImageSensorUtils::CalculatePhysicalSensorHeight(m_pSensorData)' in text
    assert 'pixelPitchInMM = (static_cast<FLOAT>(m_pSensorData->sensorProperty.pixelSize)) / divisor' in text
    decoder = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
    fragments = {hex(a): '\n'.join(f'{i.address:x}: {i.mnemonic} {i.op_str}' for i in decoder.disasm(at(a, z - a), a))
                 for a, z in [(0x191114, 0x19120c), (0x4f4e08, 0x4f4e84)]}
    private = dict(stage=487, cases=cases, hal_sha256=sha(hal), fragments=fragments,
                   schema_sha256=sha(schema), reference_source_sha256=sha(source))
    (OUT / 'metadata-native-evidence-private.json').write_text(json.dumps(private, indent=2) + '\n')
    report = dict(stage=487, passed=True, scope='retained same-handset sensor metadata, no hardware execution',
        models={'s5kgw1': dict(unit_cell_nm=[800, 800], original_pixel_um=0.8, sources=2),
                'imx319': dict(unit_cell_nm=[1400, 1400], original_pixel_um=1.4, sources=2),
                's5k3m5': dict(unit_cell_nm=[1000, 1000], original_pixel_um=1.0, sources=2),
                'imx471': dict(unit_cell_nm=[1000, 1000], original_pixel_um=1.0, sources=2, entry_already_present=True)},
        native_root_parser=dict(start='0x191114', stop='0x19120c', serialized_qwords=[92, 93, 94], native_offsets=[600, 608, 616]),
        actual_hal_consumer=dict(start='0x4f4e08', stop='0x4f4e84', instructions=31,
            scalar_pixel_size_used_on_both_axes=True, divides_by_1000_for_physical_size=True,
            independent_fixture_axes=[1000, 2000], unit='micrometres -> millimetres; libcamera UnitCellSize uses nanometres'),
        cases=len(cases), actual_descriptors=len(descriptors), distinct_sentinel=True,
        matching_sensor_property_tail_schema=True, full_newer_schema_compatibility_claimed=False,
        cached_authoritative_conflicting_same_sensor_value_found=False,
        hal_sha256=sha(hal), schema_sha256=sha(schema), reference_source_sha256=sha(source),
        private_evidence_sha256=sha(OUT / 'metadata-native-evidence-private.json'),
        rotation_values_adopted=False, oem_roll_is_not_linux_rotation=True,
        sensor_delays_adopted=False, no_ssh=True, no_sdk=True, no_compile=True, no_phone=True)
    (HERE / 'metadata-evidence-validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(passed=True, cases=len(cases), models=report['models'], rotation_adopted=False)))


if __name__ == '__main__':
    main()
