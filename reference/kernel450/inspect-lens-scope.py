"""Offline lens/portrait evidence audit; no phone, SDK, builds or deployment."""
from pathlib import Path
import hashlib
import importlib.util
import json
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET
import os
import re
import resource
import shutil
import signal

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel450/lens-scope')
spec = importlib.util.spec_from_file_location('lens_scope_storage449', HERE.parent / 'kernel449/storage.py')
storage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(storage)
BUILD = storage.mount.mounted_build()


class Description:
    def __init__(self, path):
        self.path = Path(path)
        self.raw = self.path.read_bytes()
        assert self.raw.startswith(b'QTI Chromatix Header')
        assert struct.unpack_from('<I', self.raw, 28)[0] == len(self.raw)
        table, count = struct.unpack_from('<II', self.raw, 0x98)
        assert count == 3
        self.sections = [struct.unpack_from('<QQQ', self.raw, table + i * 24) for i in range(count)]
        _, start, length = self.sections[0]
        _, self.base, size = self.sections[1]
        assert start + length <= len(self.raw) and self.base + size <= len(self.raw) and length % 72 == 0
        self.entries = {}
        for pos in range(start, start + length, 72):
            uid = struct.unpack_from('<Q', self.raw, pos)[0]
            name = self.raw[pos + 8:pos + 40].split(bytes([0]))[0].decode()
            offset, length = struct.unpack_from('<QQ', self.raw, pos + 56)
            assert offset <= size and length <= size - offset and uid not in self.entries
            self.entries[uid] = dict(name=name, offset=offset, size=length)

    def payload(self, uid):
        entry = self.entries[uid]
        return self.raw[self.base + entry['offset']:self.base + entry['offset'] + entry['size']]

    def find(self, name):
        return [(uid, self.payload(uid)) for uid, entry in self.entries.items() if entry['name'] == name]

    def one(self, name):
        found = self.find(name)
        assert len(found) == 1, (name, len(found))
        return found[0]

    def words(self, uid):
        raw = self.payload(uid)
        assert len(raw) % 8 == 0
        return struct.unpack('<' + 'Q' * (len(raw) // 8), raw)

    def regs(self, uid, count):
        raw = self.payload(uid)
        assert len(raw) == count * 80
        result = []
        for offset in range(0, len(raw), 80):
            f = struct.unpack_from('<10Q', raw, offset)
            assert f[0] in [0, 1] and f[5] in [1, 2] and f[6] in [1, 2] and f[7] in [0, 1, 2]
            data, delay = self.payload(f[4]), self.payload(f[9])
            assert len(data) == (f[3] * 4 + 7) // 8 * 8 and len(delay) == (f[8] * 4 + 7) // 8 * 8
            assert f[0] == 0, 'Optional per-record slave override requires separate decoding'
            result.append(dict(address=f[2], address_bytes=f[5], value_bytes=f[6], operation=f[7],
                               values=list(struct.unpack_from('<' + 'I' * f[3], data)), delays_us=list(struct.unpack_from('<' + 'I' * f[8], delay))))
        return result

    def string(self, payload):
        if payload and all(c == 0 or 32 <= c < 127 for c in payload):
            return payload.rstrip(bytes([0])).decode()
        if len(payload) == 16:
            count, uid = struct.unpack('<QQ', payload)
            if uid in self.entries:
                raw = self.payload(uid)
                if len(raw) == (count + 7) // 8 * 8 and all(c == 0 or 32 <= c < 127 for c in raw):
                    return raw[:count].rstrip(bytes([0])).decode()
        return None


def initial_inventory():
    folder = PRIVATE.parent.parent / 'kernel115/vendor-camera-bins'
    paths = sorted(folder.glob('com.qti.sensormodule.*.bin'))
    paths.append(PRIVATE.parent.parent / 'kernel282/shine-ov02a1b-module-private.bin')
    rows = []
    private = []
    for path in paths:
        d = Description(path)
        names = {name: [d.string(raw) for _, raw in d.find(name)] for name in ['moduleName', 'sensorName', 'actuatorName', 'eepromName']}
        summary = dict(file=path.name, bytes=len(d.raw), sha256=hashlib.sha256(d.raw).hexdigest(), names=names,
                       actuator_driver_count=len(d.find('actuatorDriver')), eeprom_driver_count=len(d.find('EEPROMDriverData')))
        rows.append(summary)
        private.append(dict(**summary, entries=[dict(uid=uid, **entry) for uid, entry in d.entries.items()]))
    PRIVATE.mkdir(exist_ok=True)
    (PRIVATE / 'inventory-private.json').write_text(json.dumps(private, indent=2) + '\n')
    return rows


def explore():
    repo = '/home/cy122/workspace/realmeX2pro-AndroidR-droidspaces/source'
    commit = '23172a1571bd91156032cc9fef16284a82b63d2c'
    dts = subprocess.check_output(['git', '-C', repo, 'show', commit + ':arch/arm64/boot/dts/19781/sm8150-camera-sensor-mtp.dtsi'], text=True)
    (PRIVATE / '19781-sensor-mtp-private.dtsi').write_text(dts)
    return dts


def decode_actuator(d):
    uid, raw = d.one('actuatorDriver')
    w = d.words(uid)
    assert len(w) == 28 and w[:3] == (1, 0, 0)
    name = d.payload(w[4]).split(bytes([0]))[0].decode()
    assert w[3] == len(name) + 1 and w[5] % 2 == 0 and w[8] == 10
    params = d.payload(w[14])
    assert len(params) == w[13] * 72
    position = [list(struct.unpack_from('<9Q', params, i * 72)) for i in range(w[13])]
    powers = {}
    for label, off in [('up', 9), ('down', 11)]:
        b = d.payload(w[off + 1])
        assert len(b) == w[off] * 24
        powers[label] = [list(struct.unpack_from('<3Q', b, i * 24)) for i in range(w[off])]
    regions_raw = d.payload(w[21])
    assert len(regions_raw) == w[20] * 32
    regions = [list(struct.unpack_from('<4Q', regions_raw, i * 32)) for i in range(w[20])]
    return dict(source_sha256=hashlib.sha256(d.raw).hexdigest(), name=name, address8=w[5], address7=w[5] >> 1,
                frequency_mode=w[6], actuator_type=w[7], data_bits=w[8], power=powers,
                position=position, init=d.regs(w[16], w[15]), deinit_count=w[17],
                initial_code=w[19], regions=regions)


def detailed_decode():
    folder = PRIVATE.parent.parent / 'kernel115/vendor-camera-bins'
    rows = []
    for name in ['sunny_imx319', 'qtech_imx319', 'qtech_s5k3m5sx']:
        d = Description(folder / ('com.qti.sensormodule.' + name + '.bin'))
        rows.append(dict(module=name, **decode_actuator(d)))
    factory = Description(PRIVATE.parent.parent / 'kernel326/qtech_s5k3m5sx-description-private.bin')
    rows.append(dict(module='qtech_s5k3m5sx-current326', **decode_actuator(factory)))
    expected_sources = {
        'sunny_imx319': 'e2d68359e85af97dbc686d63ca140ae2af87542023245c7307a57d3aeba21704',
        'qtech_imx319': 'e3f572ec006e7f7b9e729294ef258363893671733ba6e37eb9a235b4d36e4b5c',
        'qtech_s5k3m5sx': 'e3877077fa39e9a6d7bcd5cc5a56b4139c2b49f2abeb892eb4816f162472c488',
        'qtech_s5k3m5sx-current326': '823404fcc1d9cf3afa4fa126ecfa456d160188e594a9defd0bf519786988bc77',
    }
    assert all(row['source_sha256'] == expected_sources[row['module']] for row in rows)
    old_tele, new_tele = rows[2:]
    assert all(old_tele[k] == new_tele[k] for k in old_tele if k not in ['module', 'source_sha256'])
    d = Description(PRIVATE.parent.parent / 'kernel282/shine-ov02a1b-module-private.bin')
    assert hashlib.sha256(d.raw).hexdigest() == '63e2122a9b0003ed8af6eade006e3a5ef7c40beb530fa0d5a6069836e9b3b5fa'
    w = d.words(d.one('sensorDriverData')[0])
    assert len(w) == 102 and w[:3] == (1, 0, 0)
    powers = {}
    for label, count_offset in [('up', 12), ('down', 14)]:
        b = d.payload(w[count_offset + 1])
        assert len(b) == w[count_offset] * 24
        powers[label] = [list(struct.unpack_from('<3Q', b, i * 24)) for i in range(w[count_offset])]
    ri = d.words(d.one('resolutionInfo')[0]); assert len(ri) == 4 and ri[2] == 1
    f = d.words(ri[3]); assert len(f) == 32 and f[1] == 1
    streams = d.words(f[2]); assert len(streams) == 8
    initinfo = d.words(d.one('initSettings')[0])
    sensor = dict(source_sha256=hashlib.sha256(d.raw).hexdigest(), address8=w[5], address7=w[5] >> 1,
                  register_address_bytes=w[6], register_value_bytes=w[7], id_address=w[8], expected_id=w[9], id_mask=w[10],
                  power=powers, streams=[dict(vc=streams[0], data_type=streams[1], width=streams[4], height=streams[5], bits=streams[6])],
                  mode=dict(color_filter_arrangement=f[0], color_filter_name='BAYER_Y' if f[0] == 4 else 'unverified', line_length=f[3], frame_length=f[4], output_pixel_clock=f[7], lanes=f[11], three_phase=f[15], fps=struct.unpack('<d', struct.pack('<Q', f[10]))[0]),
                  init=d.regs(initinfo[2], initinfo[1]), mode_registers=d.regs(f[19], f[18]),
                  stream_on=d.regs(w[58], w[57]), stream_off=d.regs(w[60], w[59]),
                  group_hold_on=d.regs(w[62], w[61]), group_hold_off=d.regs(w[64], w[63]))
    (PRIVATE / 'decoded-private.json').write_text(json.dumps(dict(actuators=rows, portrait=sensor), indent=2) + '\n')
    return rows, sensor


def source_audit():
    source = BUILD.parent / 'source354'
    head = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    rows = []
    for name in ['sm8150-samurai.dts', 'imx319.dtsi', 's5k3m5-samurai.dtsi', 's5kgw1-samurai.dtsi']:
        path = source / 'arch/arm64/boot/dts/qcom' / name
        raw = path.read_bytes()
        (PRIVATE / ('current-' + name)).write_bytes(raw)
        text = raw.decode()
        rows.append(dict(path=str(path.relative_to(source)), sha256=hashlib.sha256(raw).hexdigest(), lens_focus_count=text.count('lens-focus'), bu64253_mentioned='bu64253' in text))
    i2c = source / 'drivers/media/i2c'
    bu = [p.name for p in i2c.glob('*bu64*')]
    (PRIVATE / 'source-audit-private.json').write_text(json.dumps(dict(head=head, files=rows, bu64_driver_files=bu), indent=2) + '\n')
    pipeline = BUILD.parent / 'libcamera450-stats-retirement/src/libcamera-v0.7.2/src/libcamera/pipeline/camss-vfe/camss_vfe.cpp'
    if pipeline.exists():
        text = pipeline.read_text()
        lines = text.splitlines()
        selected = set()
        for i, line in enumerate(lines):
            if 'lens' in line.lower() or 'focusactive' in line.lower():
                selected.update(range(max(0, i - 3), min(len(lines), i + 5)))
        (PRIVATE / 'pipeline-focus-selection-private.txt').write_text('\n'.join(f'{i+1}: {lines[i]}' for i in sorted(selected)) + '\n')
    camss = source / 'drivers/media/platform/qcom/camss'
    return dict(head=head, files=rows, bu64_driver_files=bu, ov02a1b_driver=(i2c / 'ov02a1b.c').exists(), ov02a10_driver=(i2c / 'ov02a10.c').exists(),
                camss_y10_mbus_mentions=[p.name for p in camss.glob('*.c') if 'MEDIA_BUS_FMT_Y10_1X10' in p.read_text()])


def crosscheck_actuators(expected_rows):
    parser = Path('/home/cy122/x2pro-linux/parser-k117')
    schema_source = PRIVATE.parent.parent / 'kernel117/CamxChi/chi-cdk/api/sensor'
    ns = {'x': 'http://www.w3.org/2001/XMLSchema'}
    summaries = []
    for expected in expected_rows:
        if expected['module'] not in ['sunny_imx319', 'qtech_s5k3m5sx-current326']:
            continue
        work = PRIVATE / ('parser-' + expected['module'])
        marker = work / 'crosscheck-private.json'
        if marker.exists():
            summaries.append(json.loads(marker.read_text()))
            continue
        work.mkdir(exist_ok=False)
        schema = work / 'api/sensor'; schema.mkdir(parents=True)
        for name in ['camxactuatordriver.xsd', 'camxsensorcommon.xsd']:
            shutil.copyfile(schema_source / name, schema / name)
        tree = ET.parse(schema / 'camxactuatordriver.xsd')
        sequence = tree.find("./x:complexType[@name='ActuatorSlaveInfo']/x:sequence", ns)
        sequence.remove(sequence.find("x:element[@name='actuatorID']", ns))
        tree.write(schema / 'camxactuatordriver.xsd')
        if expected['module'].endswith('-current326'):
            original = PRIVATE.parent.parent / 'kernel326/qtech_s5k3m5sx-description-private.bin'
        else:
            original = PRIVATE.parent.parent / 'kernel115/vendor-camera-bins/com.qti.sensormodule.sunny_imx319.bin'
        raw = original.read_bytes(); data = bytearray(raw)
        table, count = struct.unpack_from('<II', raw, 0x98)
        sections = [struct.unpack_from('<QQQ', raw, table + i * 24) for i in range(count)]
        _, offset, size = sections[0]; allowed = set()
        for pos in range(offset, offset + size, 72):
            name = raw[pos + 8:pos + 40].split(bytes([0]))[0].decode()
            if struct.unpack_from('<I', raw, pos + 40)[0] == 1 and name != 'actuatorDriver':
                struct.pack_into('<I', data, pos + 40, 0); allowed.update(range(pos + 40, pos + 44))
        assert all(i in allowed for i, (x, y) in enumerate(zip(raw, data)) if x != y)
        for _, off, size in sections[1:]:
            assert data[off:off + size] == raw[off:off + size]
        analysis = work / 'analysis-private.bin'; analysis.write_bytes(data)
        dest = work / 'xml'; dest.mkdir()
        for path in [work, *work.rglob('*')]:
            os.chown(path, 1000, 1000)
        def limits():
            resource.setrlimit(resource.RLIMIT_AS, (256 * 1024**2, 256 * 1024**2))
            resource.setrlimit(resource.RLIMIT_CPU, (15, 15))
            resource.setrlimit(resource.RLIMIT_FSIZE, (64 * 1024**2, 64 * 1024**2))
        with (work / 'reader-private.log').open('xb') as log:
            proc = subprocess.Popen(['stdbuf', '-oL', '-eL', str(parser / 'ParameterParser'), str(dest), 'x', str(schema), '-b' + str(analysis)],
                                    cwd=work, env=dict(os.environ, LD_LIBRARY_PATH=str(parser / 'runtime/lib')),
                                    user=1000, group=1000, start_new_session=True, stdin=subprocess.DEVNULL, stdout=log, stderr=log, preexec_fn=limits)
            try:
                ret = proc.wait(timeout=20)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL); proc.wait(timeout=3)
                raise RuntimeError('Bounded reader timed out; inspect retained evidence')
        assert ret == 0, (expected['module'], ret)
        found = list(dest.rglob('actuatorDriver.xml')); assert len(found) == 1
        xml = ET.parse(found[0]).getroot(); slave = xml.find('slaveInfo')
        assert slave.findtext('actuatorName') == expected['name']
        assert int(slave.findtext('slaveAddress')) == expected['address8']
        assert int(slave.findtext('dataBitWidth')) == expected['data_bits']
        init = [dict(address=int(x.findtext('registerAddr')), address_bytes=int(x.findtext('regAddrType')), value_bytes=int(x.findtext('regDataType')), operation=0,
                     values=[int(x.findtext('registerData'))], delays_us=[int(x.findtext('delayUs'))]) for x in xml.findall('initSettings/regSetting')]
        assert init == expected['init']
        position = [[int(x.findtext(k)) if k != 'operation' else ['WRITE_HW_DAMP', 'WRITE_DAC_VALUE', 'WRITE', 'WRITE_DIR_REG', 'POLL', 'READ_WRITE'].index(x.findtext(k))
                     for k in ['regAddrType', 'regDataType', 'registerAddr', 'registerData', 'operation', 'delayUs', 'hwMask', 'hwShift', 'dataShift']]
                    for x in xml.findall('registerConfig/registerParam')]
        assert position == expected['position']
        assert int(xml.findtext('tunedParams/initialCode')) == expected['initial_code']
        summary = dict(module=expected['module'], parser_exit=ret, address_width_init_position_initial_code_match=True,
                       payload_sections_unchanged=True, xml_sha256=hashlib.sha256(found[0].read_bytes()).hexdigest())
        marker.write_text(json.dumps(summary, indent=2) + '\n'); summaries.append(summary)
    return summaries


def stock_transport_disassembly():
    binary = PRIVATE.parent.parent / 'kernel281/camera.qcom.so-private'
    assert hashlib.sha256(binary.read_bytes()).hexdigest() == 'e2b1b9b6379507052464d9f9573c2a5a1b1cf37c43947b53645ddc8948a70dde'
    for name, begin, end in [('move-focus', 0x41dc40, 0x41e638), ('actuator-data', 0x4cb000, 0x4cda00)]:
        text = subprocess.check_output(['aarch64-linux-gnu-objdump', '-d', '--start-address=' + hex(begin), '--stop-address=' + hex(end), str(binary)], text=True)
        (PRIVATE / (name + '-disasm-private.txt')).write_text(text)
        if name == 'move-focus':
            print('\n'.join(line for line in text.splitlines() if re.search(r'\bbl\b', line)))


if __name__ == '__main__':
    inventory = initial_inventory()
    stock_dts = explore()
    actuators, portrait = detailed_decode()
    sources = source_audit()
    crosschecks = crosscheck_actuators(actuators) if '--crosscheck' in sys.argv else []
    if '--stock' in sys.argv:
        stock_transport_disassembly()
    report = dict(stage=450, scope='offline-lens-and-portrait-identification', modules=inventory, source=sources,
                  stock_dts_sha256=hashlib.sha256(stock_dts.encode()).hexdigest(),
                  actuators=[{k:v for k,v in row.items() if k not in ['initial_code', 'regions', 'power']} for row in actuators],
                  portrait={k:v for k,v in portrait.items() if k not in ['init', 'mode_registers', 'stream_on', 'stream_off', 'group_hold_on', 'group_hold_off']},
                  portrait_init_records=len(portrait['init']), portrait_mode_records=len(portrait['mode_registers']),
                  independent_actuator_crosschecks=crosschecks, no_phone_sdk_build_deployment=True,
                  physical_bu64253_identity_verified=False, portrait_chip_id_verified=False,
                  portrait_driver_usable=False, complete_camera_goal=False, passed=bool(len(crosschecks) == 2))
    (HERE / 'lens-scope-validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(passed=report['passed'], source=sources, actuator_crosschecks=crosschecks, portrait_init_records=len(portrait['init'])), indent=2))
