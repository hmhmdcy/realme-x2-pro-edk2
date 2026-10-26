"""Independent retained-mode/profile/selector/DTB checks; no device access.

Only metadata and hashes are emitted publicly. Full register sequences and IQ
objects remain in the existing private files. Frozen stages are read only.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import re
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel468')
s = importlib.util.spec_from_file_location('storage284', HERE.parent/'kernel284/storage.py')
guard = importlib.util.module_from_spec(s)
s.loader.exec_module(guard)
build = guard.mounted_build()
tree = build.parent/'source354'
libcamera = build.parent/'libcamera461-completion-ownership/src/libcamera-v0.7.2'
s = importlib.util.spec_from_file_location('storage449', HERE.parent/'kernel449/storage.py')
storage = importlib.util.module_from_spec(s)
s.loader.exec_module(storage)
sys.path.append(str(storage.SDK/'usr/lib/python3.14/site-packages'))
import yaml


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def regs(text, name):
    body = text.split(name+'[] = {', 1)[1].split('};', 1)[0]
    return [(int(a, 16), int(b, 16)) for a, b in re.findall(
        r'CCI_REG16\(0x([0-9a-f]+)\),\s*0x([0-9a-f]+)', body, re.I)]


sources = []
stock = []
for variant in ['a', 'b']:
    p = PRIVATE.parent/f'kernel239/s5k3m5-{variant}-xml-private/Scenario.0/XML/None/sensorDriverData.xml'
    modes = ET.parse(p).getroot().findall('resolutionInfo/resolutionData')
    seq = []
    for mode in modes:
        entries = mode.findall('resSettings/regSetting')
        seq.append([(int(x.findtext('registerAddr')), int(x.findtext('registerData'))) for x in entries])
    mode = modes[2]
    assert mode.findtext('capability') == 'HFR'
    assert all(x.findtext('operation') == 'WRITE' and x.findtext('delayUs') == '0' and
               x.findtext('regDataType') == x.findtext('regAddrType') == '2'
               for x in mode.findall('resSettings/regSetting'))
    assert int(mode.findtext('lineLengthPixelClock')) == 4848
    assert int(mode.findtext('frameLengthLines')) == 3312
    stock.append(seq)
    sources.append(dict(path=str(p.relative_to(PRIVATE.parent)), sha256=sha(p)))
assert stock[0] == stock[1]
stock = stock[1]
header = PRIVATE/'candidate/drivers/media/i2c/s5k3m5-19mhz-tables.h'
old_header = PRIVATE/'baseline/drivers/media/i2c/s5k3m5-19mhz-tables.h'
assert header.read_bytes().startswith(old_header.read_bytes())
assert regs(header.read_text(), 's5k3m5_clock19_mode2_regs') == stock[2]
assert len(stock[2]) == 53
assert regs(header.read_text(), 's5k3m5_clock19_mode3_regs') == stock[3]
retained = PRIVATE.parent/'kernel465/s5k3m5-mode2-draft-regs-private.h'
assert regs(retained.read_text(), 's5k3m5_clock19_mode2_regs') == stock[2]
r2, r0 = dict(stock[2]), dict(stock[0])
assert [r2[0x34c], r2[0x34e], r2[0x342], r2[0x340]] == [4208, 2368, 4848, 3312]
origin = lambda r: [r[0x344]+r[0x350], r[0x346]+r[0x352]]
crop_origin = [a-b for a, b in zip(origin(r2), origin(r0))]
assert crop_origin == [0, 376]

base_path = PRIVATE.parent/'kernel440/factory-s5k3m5-private.yaml'
draft_path = PRIVATE.parent/'kernel465/factory-s5k3m5-mode2-draft-private.yaml'
profile_path = PRIVATE/'factory-s5k3m5-mode2-private.yaml'
assert sha(profile_path) == sha(draft_path)
base = yaml.safe_load(base_path.read_text())['modes'][0]
modes = yaml.safe_load(profile_path.read_text())['modes']
assert len(modes) == 2 and modes[0] == base
new = modes[1]
expected_match = dict(width=4208, height=2368, pixel_rate=481930000, line_length=4848, frame_length=3312)
assert new['match'] == expected_match
assert all(new['sensor_controls'][k] == v for k, v in expected_match.items())
assert new['sensor_controls']['exposure_delay'] == new['sensor_controls']['gain_delay'] == 2
def diff(a, b, prefix=''):
    if isinstance(a, dict) and isinstance(b, dict):
        assert a.keys() == b.keys()
        return sum((diff(a[k], b[k], prefix+'/'+k) for k in a), [])
    return [] if a == b else [prefix]
allowed = sorted(['/'+kind+'/'+field for kind in ['match','sensor_controls']
                  for field in ['width','height','line_length','frame_length']]+
                 ['/lens_shading/first_quad','/lens_shading/quad_step'])
assert sorted(diff(base, new)) == allowed
geometry = new['lens_shading']
assert geometry['first_quad'] == [0, 188] and geometry['quad_step'] == [1, 1]
assert geometry['source_span'] == [2103, 1559]
last = [geometry['first_quad'][i]+(new['match'][dim]/2-1)*geometry['quad_step'][i]
        for i, dim in enumerate(['width','height'])]
assert last == [2103, 1371]

def f32(v):
    return struct.unpack('f', struct.pack('f', v))[0]
def select(request, available):
    ratio = f32(f32(request[0])/request[1])
    candidates = []
    for mode in available:
        if mode[0] < request[0] or mode[1] < request[1]:
            continue
        delta = abs(f32(f32(f32(mode[0])/mode[1])-ratio))
        candidates.append((delta, mode[0]*mode[1]-request[0]*request[1], mode))
    return min(candidates)[2] if candidates else None
available = [(2104,1560), (4208,2368)]
selection = []
for request in [(1280,720), (1920,1080), (640,480), (2104,1560), (4208,2368)]:
    result = select(request, available)
    selection.append(dict(request=list(request), sensor_mode=list(result),
                          explicit_sensor_config=request in available))
assert selection[0]['sensor_mode'] == selection[1]['sensor_mode'] == [4208,2368]
assert selection[3]['sensor_mode'] == [2104,1560]

# Extract the exact frozen363 FAT's DTB, without mounting or running packaging.
fat = PRIVATE.parent/'kernel363/logdump-k363-candidate-private.img'
assert sha(fat) == '1869c02f9ad648d334415206e3c53a75ba3fc771fb6cfb3ef7ef586bab1b5a83'
dtb = subprocess.check_output(['mcopy','-i',str(fat),'::/samurai.dtb','-'], timeout=30)
dtb_hash = hashlib.sha256(dtb).hexdigest()
assert dtb_hash == 'dcdd74ec903520c7023fa28badcb293b2e4e26ee5bac639497c63d53536b2c8d'
(PRIVATE/'frozen363-samurai.dtb').write_bytes(dtb)
magic, total, off_struct, off_strings = struct.unpack_from('>4I', dtb)
assert magic == 0xd00dfeed and total == len(dtb)
props = {}; stack = []; pos = off_struct
def cstring(offset):
    return dtb[offset:dtb.index(b'\0', offset)].decode()
while True:
    token, = struct.unpack_from('>I', dtb, pos); pos += 4
    if token == 1:
        name = cstring(pos); pos = (pos+len(name.encode())+1+3)&~3
        stack.append(name)
    elif token == 2:
        stack.pop()
    elif token == 3:
        length, nameoff = struct.unpack_from('>2I',dtb,pos); pos += 8
        name = cstring(off_strings+nameoff)
        path = '/'+('/'.join(x for x in stack if x))
        props.setdefault(path,{})[name] = dtb[pos:pos+length]
        pos = (pos+length+3)&~3
    elif token == 4:
        continue
    elif token == 9:
        break
    else:
        raise ValueError(token)
sensor_paths = [p for p, values in props.items() if b'samsung,s5k3m5\0' in values.get('compatible',b'')]
assert len(sensor_paths) == 1
endpoints = [(p,v) for p,v in props.items() if p.startswith(sensor_paths[0]+'/') and 'link-frequencies' in v]
assert len(endpoints) == 1
endpoint, values = endpoints[0]
links = list(struct.unpack('>'+('Q'*(len(values['link-frequencies'])//8)),values['link-frequencies']))
lanes = list(struct.unpack('>'+('I'*(len(values['data-lanes'])//4)),values['data-lanes']))
assert links == [723200000] and lanes == [1,2,3,4]
current_dtsi = tree/'arch/arm64/boot/dts/qcom/s5k3m5-samurai.dtsi'
assert 'link-frequencies = /bits/ 64 <723200000>;' in current_dtsi.read_text()

evidence = []
for root, rels in [(tree, ['drivers/media/v4l2-core/v4l2-ctrls-api.c',
    'drivers/media/v4l2-core/v4l2-ctrls-core.c','drivers/media/i2c/imx319.c',
    'drivers/media/i2c/imx471.c','arch/arm64/boot/dts/qcom/s5k3m5-samurai.dtsi',
    'arch/arm64/boot/dts/qcom/sm8150-samurai.dts']),
    (libcamera, ['src/libcamera/sensor/camera_sensor_legacy.cpp',
    'src/libcamera/pipeline/camss-vfe/camss_vfe.cpp','src/ipa/camss-vfe/camss.cpp'])]:
    for rel in rels:
        p=root/rel
        evidence.append(dict(path=str(p), sha256=sha(p)))
candidate = PRIVATE/'candidate/drivers/media/i2c/s5k3m5.c'
report = dict(stage=468, reviewer='independent offline mode/control review',
    script_sha256=sha(Path(__file__)), candidate_sha256=sha(candidate), header_sha256=sha(header),
    stock_xml_sources=sources, stock_mode2_exact_ordered_writes=53,
    stock_mode2_capability='HFR', stock_mode2_declared_fps=30,
    mode3_header_byte_prefix_preserved=True, mode3_profile_unchanged=True,
    stock_full_table_public=False, mode2_match=expected_match, mode2_crop=crop_origin+[4208,2368],
    geometry={k:geometry[k] for k in ['source_span','first_quad','quad_step']},
    lsc_last_quad=last, all_other_iq_fields_exactly_reused=True,
    profile_sha256=sha(profile_path), clock_source='inherited mode3 control timing; physical mode2 timing pending',
    control_pixel_rate_hz=481930000, transport_pixel_rate_hz=578560000,
    line_duration_us=4848*1000000/481930000, default_frame_duration_us=3312*4848*1000000/481930000,
    default_frame_rate_hz=481930000/(3312*4848), hblank=640, vblank=dict(min=944,max=63167,default=944),
    exposure_lines=dict(min=1,max=3308,default=256), exposure_gain_delays_frames=[2,2],
    delays_physically_verified_for_mode2=False, selector_float32_results=selection,
    explicit_mode3_capture_stays_mode3=True,
    frozen363_dtb=dict(sha256=dtb_hash,bytes=len(dtb),endpoint=endpoint,link_frequencies_hz=links,data_lanes=lanes,
                      source_fat_sha256=sha(fat)),
    current_dtsi_allows_723200000=True, source_evidence=evidence,
    boundaries=['VT/control rate and two-frame delays inherited, require mode2 hardware timing confirmation',
                'LSC reference convention inherited from321/323; exact target HAL assignment unproven',
                'mode3 existing723.2MHz declaration preserved;466 lower candidate not deployed',
                'Selector result is a source-derived bounded model, not an executed CameraSensorLegacy binary',
                'Mode2 streaming, correct crop, PD10 same-SOF and LTM consumption not hardware-verified here'],
    phone_accessed=False, sdk_bound=False, shared_source_modified=False, frozen465_466_modified=False, passed=True)
(HERE/'mode-review-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['stock_xml_sources','source_evidence','boundaries']},indent=2))
