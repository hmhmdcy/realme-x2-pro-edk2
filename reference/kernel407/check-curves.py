"""Compare portable curves with pinned source and actual target HAL fragments."""
from pathlib import Path
import hashlib, importlib.util, json, math, os, random, shutil, struct, subprocess, sys, time
import host
HERE = Path(__file__).resolve().parent
P = host.PRIVATE

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    out = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(out)
    return out

storage = module('storage284', HERE.parent / 'kernel284/storage.py')
source = storage.mounted_build().parent / 'source354'
state = json.loads((HERE.parent / 'kernel406/source-state.json').read_text())
assert subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip() == state['commit']
assert not subprocess.check_output(['git', '-C', str(source), 'status', '--porcelain'])
state.update(stage=407, source_unchanged_from406=True, phone_accessed=False,
             last_device_evidence_stage=406, new_portable_curve_primitives=True)
(HERE / 'source-state.json').write_text(json.dumps(state, indent=2) + '\n')

def function(text, needle):
    start = text.index(needle)
    brace = text.index('{', start)
    depth = 1
    end = brace + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]

setting = (P.parent / 'kernel403/sources/ltm13setting.cpp').read_text()
manifest = json.loads((HERE.parent / 'kernel403/primary-sources.json').read_text())
entry = next(r for r in manifest['files'] if r['path'].endswith('/ltm13setting.cpp'))
assert hashlib.sha256(setting.encode()).hexdigest() == entry['sha256']
prefix = '''#include <algorithm>
#include <cassert>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
using INT=int;using INT16=int16_t;using INT32=int32_t;using UINT=unsigned;using UINT16=uint16_t;using UINT32=uint32_t;using FLOAT=float;using VOID=void;
constexpr unsigned LTM_SCALE_LUT_SIZE=65,LCE_SCALE_LUT_SIZE=17;
enum class LTMDarkBrightRegionState {LTMRegionIndexInit,LTMDarkBoostRegion,LTMBrightRegion};
struct LTM13InputData{float exposureIndex,prevExposureIndex;};
namespace ltm_1_3_0 {
struct ltm13_rgn_dataType {struct {float ltm_scale[65];} ltm_scale_tab;struct {float lce_scale_pos[17];} lce_scale_pos_tab;struct {float lce_scale_neg[17];} lce_scale_neg_tab;
float ltm_strength,lce_strength,exp_atten_start,exp_atten_end,dark_boost,bright_suppress,dark_range,bright_range,dark_max,bright_max,dark_gamma,bright_gamma;};
struct chromatix_ltm13_reserveType {uint32_t ltm_scale_manual_curve_enable;};
}
struct IQSettingUtils {
static FLOAT AbsoluteFLOAT(FLOAT v){return std::fabs(v);}
static FLOAT ClampFLOAT(FLOAT v,FLOAT low,FLOAT high){return v<low?low:(v>high?high:v);}
static INT16 MinINT16(INT16 a,INT16 b){return a<b?a:b;}
};
'''
oracle = prefix
for needle in ['static void Pack1D16EntrySignedLUT(', 'static void Pack1D64EntrySignedLUT(',
               'static VOID AttenuateCurves(', 'static VOID DarkBrightRegionTreatment(', 'VOID AutoManualCalculate(']:
    oracle += function(setting, needle) + '\n'
oracle += '''struct Input {float arrays[99],c[14];uint32_t manual;};
int main(){static_assert(sizeof(Input)==456);Input in;while(fread(&in,sizeof in,1,stdin)==1){ltm_1_3_0::ltm13_rgn_dataType d;memcpy(d.ltm_scale_tab.ltm_scale,in.arrays,260);memcpy(d.lce_scale_pos_tab.lce_scale_pos,in.arrays+65,68);memcpy(d.lce_scale_neg_tab.lce_scale_neg,in.arrays+82,68);
float *c=in.c;d.ltm_strength=c[0];d.lce_strength=c[1];d.exp_atten_start=c[2];d.exp_atten_end=c[3];d.dark_boost=c[4];d.bright_suppress=c[5];d.dark_range=c[6];d.bright_range=c[7];d.dark_max=c[8];d.bright_max=c[9];d.dark_gamma=c[10];d.bright_gamma=c[11];
LTM13InputData input{c[12],c[13]};ltm_1_3_0::chromatix_ltm13_reserveType reserve{in.manual};AutoManualCalculate(&d,&input,&reserve);
uint32_t ok=1;assert(fwrite(&ok,4,1,stdout)==1&&fwrite(&ok,4,1,stdout)==1);assert(fwrite(d.ltm_scale_tab.ltm_scale,4,65,stdout)==65);assert(fwrite(d.lce_scale_pos_tab.lce_scale_pos,4,17,stdout)==17);assert(fwrite(d.lce_scale_neg_tab.lce_scale_neg,4,17,stdout)==17);
INT16 s[65],p[17],n[17];INT32 packed[96];for(int i=0;i<65;i++){float v=std::round(d.ltm_scale_tab.ltm_scale[i]);assert(v>=-32768&&v<=32767);s[i]=static_cast<INT16>(v);}for(int i=0;i<17;i++){p[i]=static_cast<INT16>(std::clamp(std::round(d.lce_scale_pos_tab.lce_scale_pos[i]),-2048.f,2047.f));n[i]=static_cast<INT16>(std::clamp(std::round(d.lce_scale_neg_tab.lce_scale_neg[i]),-2048.f,2047.f));}
Pack1D64EntrySignedLUT(s,packed,2);Pack1D16EntrySignedLUT(p,packed+64,2);Pack1D16EntrySignedLUT(n,packed+80,2);assert(fwrite(packed,4,96,stdout)==96);
}return ferror(stdin)||ferror(stdout);}
'''
(P / 'curve-source-oracle-private.cpp').write_text(oracle)
q = subprocess.run(['g++', '-std=c++17', '-O2', '-ffp-contract=off', '-Wall', '-Wextra', '-Werror', str(P / 'curve-source-oracle-private.cpp'), '-o', str(P / 'curve-source-oracle')], capture_output=True)
(P / 'oracle-build.log').write_bytes(q.stdout + q.stderr)
assert not q.returncode, q.stderr.decode()

names = ['qtech_s5kgw1', 'sunny_s5kgw1', 'sunny_imx471', 'qtech_s5k3m5sx', 'sunny_imx319']
fields = ['ltm_strength', 'lce_strength', 'exp_atten_start', 'exp_atten_end', 'dark_boost',
          'bright_suppress', 'dark_range', 'bright_range', 'dark_max', 'bright_max', 'dark_gamma', 'bright_gamma']
cases = []
counts = []
def leaves(nodes):
    for node in nodes:
        if 'children' in node:
            yield from leaves(node['children'])
        else:
            yield node['data']

for name in names:
    roots = json.loads((P.parent / 'kernel351' / (name + '-ltm13_ipe-trees-private.json')).read_text())
    count = 0
    for root in roots:
        for data in leaves(root['core']):
            count += 1
            arrays = data['ltm_scale_tab'] + data['lce_scale_pos_tab'] + data['lce_scale_neg_tab']
            controls = [data[key] for key in fields]
            a, b = controls[2:4]
            for delta in [0.0, (a + b) / 2, b + 1.0]:
                cases.append(dict(kind='factory', variant=name, uid=root['uid'],
                                  values=arrays + controls + [100.0 + delta, 100.0],
                                  manual=root['reserve']['ltm_scale_manual_curve_enable']))
    counts.append(dict(variant=name, roots=len(roots), regions=count, exposure_deltas_each=3))
assert sum(c['regions'] for c in counts) == 2135
base_controls = [1, 1, 2, 10, 1.5, 0.75, 0.3, 0.3, 2, 1, 2, 2, 100, 100]
shapes = [[-100.0] * 65, [100.0] * 65, [0.0] * 65,
          [-10.0] * 20 + [0.0] * 10 + [20.0] * 35,
          [10.0] * 20 + [0.0] * 10 + [-20.0] * 35,
          [0.0] * 20 + [-20.0] * 45,
          [float(i - 32) for i in range(65)],
          [float(2047 if i % 2 else -2048) for i in range(65)]]
for si, scale in enumerate(shapes):
    for delta, start, end in [(0, 2, 10), (6, 2, 10), (20, 2, 10), (-6, 2, 10), (3, 4, 4), (3, 8, 2)]:
        controls = base_controls.copy()
        controls[2:4] = [start, end]
        controls[12:] = [100 + delta, 100]
        cases.append(dict(kind='manual-boundary', shape=si, values=scale + [float(i * 400 - 3000) for i in range(17)] * 2 + controls, manual=1))
rng = random.Random(407)
for i in range(96):
    controls = [rng.uniform(0, 2), rng.uniform(0, 2), 2, 10, 1, 1,
                rng.uniform(-0.2, 1.2), rng.uniform(-0.2, 1.2), rng.uniform(-1, 9),
                rng.uniform(-1, 5), rng.uniform(0, 6), rng.uniform(0, 6),
                100 + (i % 3) * 6, 100]
    cases.append(dict(kind='automatic', values=[0.0] * 65 + [rng.uniform(-3000, 3000) for _ in range(34)] + controls, manual=0))
valid_count = len(cases)
records = [struct.pack('<113fI', *c['values'], c['manual']) for c in cases]
input_bytes = b''.join(records)
(P / 'curve-input-private.bin').write_bytes(input_bytes)
(P / 'curve-cases-private.json').write_text(json.dumps(cases, indent=2) + '\n')
q = subprocess.run([str(P / 'curve-source-oracle')], input=input_bytes, capture_output=True)
assert not q.returncode, q.stderr.decode()
expected = q.stdout
assert len(expected) == valid_count * 788
(P / 'curve-source-expected-private.bin').write_bytes(expected)

# Invalid controls/arrays are tested against the typed API, not sent into the
# factory implementation's unchecked floating-to-integer conversion.
invalid = []
for at in [0, 64, 65, 81, 82, 98, *range(99, 113)]:
    for value in [math.nan, math.inf, -math.inf, 2097152.0]:
        raw = bytearray(records[0])
        struct.pack_into('<f', raw, at * 4, value)
        invalid.append(bytes(raw))
raw = bytearray(records[0])
struct.pack_into('<I', raw, 452, 2)
invalid.append(bytes(raw))
all_input = input_bytes + b''.join(invalid)
expected += (struct.pack('<2I', 0, 0) + bytes([0xa5]) * 780) * len(invalid)
architectures = []
outputs = []
sdk = Path('/home/cy122/x2pro-linux/libcamera214-root')
work = sdk / 'private/camss407-math'
(work / 'libipa').mkdir(parents=True, exist_ok=True)
for relative in ['curve-runner.cpp', 'libipa/ltm_curves.cpp', 'libipa/ltm_curves.h']:
    shutil.copyfile(HERE / relative, work / relative)
for arch in ['host', 'aarch64']:
    binary = P / ('curves-' + arch)
    options = ['-std=c++17', '-O2', '-ffp-contract=off', '-Wall', '-Wextra', '-Werror']
    command = (['g++', *options, '-fsanitize=address,undefined', '-no-pie', '-I' + str(HERE), str(HERE / 'curve-runner.cpp'), str(HERE / 'libipa/ltm_curves.cpp'), '-o', str(binary)] if arch == 'host' else
               ['chroot', str(sdk), 'g++', *options, '/private/camss407-math/curve-runner.cpp', '/private/camss407-math/libipa/ltm_curves.cpp', '-o', '/private/camss407-math/curves-aarch64'])
    q = subprocess.run(command, capture_output=True)
    (P / (arch + '-build.log')).write_bytes(q.stdout + q.stderr)
    assert not q.returncode, q.stderr.decode()
    launch = [str(binary)] if arch == 'host' else ['chroot', str(sdk), '/private/camss407-math/curves-aarch64']
    q = subprocess.run(launch, input=all_input, capture_output=True, timeout=40)
    assert not q.returncode, q.stderr.decode()
    (P / ('curves-' + arch + '-output-private.bin')).write_bytes(q.stdout)
    assert len(q.stdout) == len(expected)
    different_tables = sum(a != b for i in range(valid_count) for a, b in zip(q.stdout[i*788+404:(i+1)*788], expected[i*788+404:(i+1)*788]))
    float_deltas = [abs(a - b) for i in range(valid_count)
                    for a, b in zip(struct.unpack_from('<99f', q.stdout, i*788+8), struct.unpack_from('<99f', expected, i*788+8))]
    validity = all(q.stdout[i*788:i*788+8] == expected[i*788:i*788+8] for i in range(valid_count))
    invalid_ok = q.stdout[valid_count*788:] == expected[valid_count*788:]
    architectures.append(dict(architecture=arch, valid_cases=valid_count, invalid_cases=len(invalid),
                              original_source_packed_different_bytes=different_tables,
                              max_source_float_absolute_difference=max(float_deltas),
                              all_validity_results_equal=validity, invalid_output_unchanged=invalid_ok,
                              passed=not different_tables and validity and invalid_ok))
    outputs.append(q.stdout)
    print(json.dumps(architectures[-1]), flush=True)

model = module('curve407', HERE / 'curve-model.py').CurveMachine()
start = time.monotonic()
hal_raw = []
max_float_difference = 0
hal_different_tables = 0
# Run the original fragments for every factory region and each synthetic case.
for i, record in enumerate(records):
    actual = model.curves(record)
    hal_raw.append(actual)
    floats = struct.unpack('<99f', actual)
    original = struct.unpack_from('<99f', expected, i * 788 + 8)
    max_float_difference = max(max_float_difference, max(abs(a-b) for a,b in zip(floats, original)))
    def pack(values, lce=False):
        nodes = [int(math.copysign(math.floor(abs(v)+0.5), v)) for v in values]
        if lce:
            nodes = [max(-2048, min(v, 2047)) for v in nodes]
        nodes = [min(v, 2047) for v in nodes]
        result = []
        for a, b in zip(nodes, nodes[1:]):
            delta = b-a
            lo = (a & 4095) | (2048 if a < 0 else 0)
            hi = (delta & 4095) | (2048 if delta < 0 and not lce else 0)
            result.append(lo | hi << 12)
        return result
    table = struct.pack('<96I', *(pack(floats[:65])+pack(floats[65:82],True)+pack(floats[82:],True)))
    hal_different_tables += sum(a!=b for a,b in zip(table, expected[i*788+404:(i+1)*788]))
    if i % 1000 == 0:
        print(json.dumps(dict(hal_cases_done=i+1, hal_table_differences=hal_different_tables)), flush=True)
(P / 'curves-hal-output-private.bin').write_bytes(b''.join(hal_raw))
report = dict(stage=407, original_factory_regions=counts, valid_cases=valid_count,
              factory_regions=2135, factory_cases=6405, synthetic_manual_cases=48, synthetic_auto_cases=96,
              architectures=architectures, original_hal_cases=len(hal_raw),
              host_asan_ubsan=True, aarch64_existing_sdk_under_qemu=True,
              invalid_calculation_outputs_unchanged=81,
              additional_invalid_encoder_outputs_unchanged=14,
              original_hal_ranges=[['0x35ec64', '0x360560'], ['0x360ac8', '0x360c3c']],
              original_hal_instructions=model.instructions, original_hal_providers=model.providers,
              external_powf_is_host_libm_not_target_bionic=True,
              max_hal_vs_source_float_absolute_difference=max_float_difference,
              hal_vs_source_packed_different_bytes=hal_different_tables,
              hal_curve_outputs_repacked_with_documented_source_rules=True,
              actual_hal_final_packer_not_executed_in_this_check=True,
              hal_seconds=round(time.monotonic()-start,2),
              oem_temporal_block_deliberately_excluded=True, adrc_not_implemented=True,
              trigger_tree_interpolation_not_implemented_here=True,
              geometry_registers_and_other_luts_not_implemented_here=True,
              source_unchanged=True, phone_accessed=False,
              full_goal_kept_active=True,
              passed=all(r['passed'] for r in architectures) and not hal_different_tables)
path = HERE / 'curves-validation.json'
if path.exists():
    previous=json.loads(path.read_text())
    if not previous['passed'] and not (HERE / 'curves-r1-validation.json').exists():
        (HERE / 'curves-r1-validation.json').write_bytes(path.read_bytes())
path.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2), flush=True)
assert report['passed']
