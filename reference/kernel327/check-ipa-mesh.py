"""Compare the new unit configurations' real AArch64 IPA packets to Hermite math."""
from pathlib import Path
import json, math, shutil, struct, subprocess, yaml
import host

HERE = Path(__file__).resolve().parent
P = host.PRIVATE
SDK = Path('/home/cy122/x2pro-linux/libcamera214-root')
TREE = '/work/libcamera321-lsc-built/src/libcamera-v0.7.2'
stage = SDK / 'private/camss327-mesh'
stage.mkdir(exist_ok=True)
s = (HERE.parent / 'kernel322/dump-ipa-mesh.cpp').read_text()
s = s.replace('#include <cstdio>', '#include <cstdio>\n#include <string>')
s = s.replace('assert(argc==3||argc==4);', 'assert(argc==9);')
s = s.replace('ControlInfo(int32_t(0),int32_t(960),int32_t(512))',
              'ControlInfo(int32_t(32),int32_t(960),int32_t(512))')
begin = s.index('\tinfo.model="imx319";')
end = s.index('\n\tControlInfoMap controlsInfo;', begin)
s = s[:begin] + '''
 info.model=argv[3];info.outputSize=Size(std::stoul(argv[4]),std::stoul(argv[5]));info.bitsPerPixel=10;
 info.pixelRate=std::stoull(argv[6]);info.minLineLength=info.maxLineLength=std::stoul(argv[7]);
 info.minFrameLength=std::stoul(argv[8]);info.maxFrameLength=65535;''' + s[end:]
s = s.replace('IPASettings{"","imx319"}', 'IPASettings{"",info.model}')
s = s.replace('\tconst bool afSupported=controlsInfo.find(&controls::AfMode)!=controlsInfo.end();\n\tassert(afSupported==(argc==4 && std::string(argv[3])=="af"));', '')
(HERE / 'dump-ipa-mesh.cpp').write_text(s)
(stage / 'dump.cpp').write_text(s)
args = ['chroot', str(SDK), 'g++', '-std=c++20', '-O2', '-Wall', '-Wextra', '-Werror',
    '-DLIBCAMERA_BASE_PRIVATE', '-I' + TREE + '/include', '-I' + TREE + '/output/include',
    '/private/camss327-mesh/dump.cpp', '-L' + TREE + '/output/src/libcamera',
    '-L' + TREE + '/output/src/libcamera/base', '-Wl,-rpath-link,' + TREE + '/output/src/libcamera/base',
    '-lcamera', '-lcamera-base', '-ldl', '-o', '/private/camss327-mesh/dump']
q = subprocess.run(args, capture_output=True)
(P / 'mesh-build.log').write_bytes(q.stdout + q.stderr)
assert not q.returncode, q.stderr.decode()
old = (HERE.parent / 'kernel319/check-factory-resampling.py').read_text()
ns = {'math': math, 'struct': struct}
exec(old[old.index('def geometry'):old.index('\ncases=')], ns)
f32 = lambda v: struct.unpack('<f', struct.pack('<f', v))[0]
rows = []
for name, case in json.loads((HERE / 'cases.json').read_text()).items():
    profile = yaml.safe_load((P / 'profiles' / (case['profile'] + '.yaml')).read_text())
    width, height = map(int, case['sensor_size'].split('x'))
    mode = next(m for m in profile['modes'] if (m['match']['width'], m['match']['height']) == (width, height))
    match = mode['match']
    target = stage / (case['profile'] + '.yaml')
    shutil.copyfile(P / 'profiles' / target.name, target)
    q = subprocess.run(['chroot', str(SDK), 'env',
        'LD_LIBRARY_PATH=' + TREE + '/output/src/libcamera:' + TREE + '/output/src/libcamera/base',
        '/private/camss327-mesh/dump', TREE + '/output/src/ipa/camss-vfe/ipa_camss_vfe.so',
        '/private/camss327-mesh/' + target.name, case['model'], str(width), str(height),
        str(match['pixel_rate']), str(match['line_length']), str(match['frame_length'])],
        capture_output=True, timeout=45)
    (P / ('mesh-' + name + '.log')).write_bytes(q.stderr)
    assert not q.returncode, (name, q.stderr.decode())
    assert len(q.stdout) == 1792
    (P / (name + '-mesh-private.bin')).write_bytes(q.stdout)
    header = struct.unpack_from('<HHIHHHHB', q.stdout)
    grid = ns['geometry'](width, height)
    assert header[:3] == (6, 2, 1792) and header[3:] == grid
    lsc = mode['lens_shading']
    channels = ['r', 'gr', 'gb', 'b']
    source = [[f32(v) for v in lsc['gains'][c]] for c in channels]
    if case['kind'] == 'unit':
        source = [[f32(v * f32(f32(g) / f32(u))) for v, g, u in
            zip(source[i], lsc['golden'][c], lsc['unit'][c])] for i, c in enumerate(channels)]
        green = [f32(f32(a * .5) + f32(b * .5)) for a, b in zip(source[1], source[2])]
        source[1] = source[2] = green
    mapping = [*lsc['source_span'], *lsc['first_quad'], *lsc['quad_step']]
    expected = [math.floor(v * 1024 + .5) for channel in source for v in ns['predict'](channel, grid, mapping)]
    actual = struct.unpack_from('<884H', q.stdout, 24)
    errors = sum(a != b for a, b in zip(actual, expected))
    rows.append(dict(case=name, words=len(actual), differing_q10_values=errors, grid=grid))
    assert errors == 0, rows[-1]
report = dict(stage=327, actual_aarch64_ipa_dso=True, independent_python_hermite_model=True,
    cases=rows, compared_values=sum(r['words'] for r in rows),
    differing_values=sum(r['differing_q10_values'] for r in rows), passed=True)
(HERE / 'ipa-mesh-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(dict(stage=327, cases=len(rows), compared_values=report['compared_values'], differing_values=0, passed=True)))
