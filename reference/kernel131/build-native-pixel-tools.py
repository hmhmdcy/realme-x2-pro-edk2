#!/usr/bin/env python3
"""Build both controls from identical source, differing only in FBO dimensions."""
import ast
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile
import time

work = Path('/tmp/k131-native-sdk')
src = work / 'glmark2-2023.01'
sdk = work / 'sdk'
build = work / 'build'
build.mkdir(mode=0o700, exist_ok=True)
assert not (build / 'build-receipts.json').exists()
env = dict(os.environ)
env['PATH'] = str(sdk / 'usr/bin') + ':' + env['PATH']
env['LD_LIBRARY_PATH'] = str(sdk / 'usr/lib')
env['GCC_EXEC_PREFIX'] = str(sdk / 'usr/lib/gcc') + '/'
cxx = str(sdk / 'usr/bin/g++')
cc = str(sdk / 'usr/bin/gcc')
base = ['--sysroot=' + str(sdk), '-B' + str(sdk / 'usr/bin'),
        '-O2', '-g1', '-DUSE_EXCEPTIONS', '-DGLMARK2_USE_GLESv2',
        '-DGLMARK2_USE_EGL', '-DGLMARK2_USE_WAYLAND', '-DWL_EGL_PLATFORM',
        '-DGLMARK_VERSION="2023.01-k131-control"',
        '-DGLMARK2_EXECUTABLE="glmark2-es2-wayland"',
        '-DGLMARK_DATA_PATH="/tmp/k131-glmark2/usr/share/glmark2"',
        '-I' + str(src / 'src'), '-I' + str(src / 'src/libmatrix'),
        '-I' + str(src / 'src/glad/include'),
        '-I' + str(src / 'src/scene-ideas'), '-I' + str(src / 'src/scene-terrain'),
        '-I' + str(sdk / 'usr/include/libpng16'), '-I' + str(build)]

def command(args):
    subprocess.run(args, env=env, check=True, timeout=90)

print('COMPILER', flush=True)
command([cxx, '--version'])
scanner = sdk / 'usr/bin/wayland-scanner'
xml = sdk / 'usr/share/wayland-protocols/stable/xdg-shell/xdg-shell.xml'
command([str(scanner), 'client-header', str(xml), str(build / 'xdg-shell-client-protocol.h')])
command([str(scanner), 'private-code', str(xml), str(build / 'xdg-shell-protocol.c')])
meson = (src / 'src/meson.build').read_text()
common = ast.literal_eval(re.search(r'common_sources\s*=\s*(\[.*?\])', meson, re.S).group(1))
names = [name for name in common if name != 'canvas-generic.cpp']
names += ['native-state-wayland.cpp', 'gl-state-egl.cpp', 'main.cpp',
          'glad/src/gles2.c', 'glad/src/egl.c']
objects = []
start = time.monotonic()
with tarfile.open(work / 'inputs/glmark2-2023.01.tar.gz') as archive:
    for name in names:
        assert (src / 'src' / name).read_bytes() == archive.extractfile('glmark2-2023.01/src/' + name).read()
reuse = []
for i, name in enumerate(names + ['GENERATED:xdg-shell-protocol.c']):
    source = build / name.split(':')[1] if name.startswith('GENERATED:') else src / 'src' / name
    obj = build / ('common-%03d.o' % i)
    is_c = str(source).endswith('.c')
    if os.environ.get('K131_REUSE_COMMON_OBJECTS') == '1' and obj.is_file():
        assert obj.stat().st_size > 0
        reuse.append({'source': name, 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                      'object_sha256': hashlib.sha256(obj.read_bytes()).hexdigest()})
    else:
        command([cc if is_c else cxx] + base + ([] if is_c else ['-std=c++14']) + ['-c', str(source), '-o', str(obj)])
    objects.append(str(obj))
    if i % 10 == 0:
        print('COMPILED', i + 1, 'elapsed', round(time.monotonic() - start, 1), flush=True)

(build / 'common-reuse-private.json').write_text(json.dumps(reuse, indent=2) + '\n')
original = (src / 'src/canvas-generic.cpp').read_text()
# Add identical read-only framebuffer diagnostics to both variants.
anchor = '    do_make_current();\n\n    std::stringstream ss;'
diagnostic = '''    do_make_current();
    if (offscreen_) {
        GLint actual_width = 0, actual_height = 0;
        glGetRenderbufferParameteriv(GL_RENDERBUFFER, GL_RENDERBUFFER_WIDTH, &actual_width);
        glGetRenderbufferParameteriv(GL_RENDERBUFFER, GL_RENDERBUFFER_HEIGHT, &actual_height);
        Log::info("    Actual FBO Size: %dx%d; Canvas Size: %dx%d\\n",
                  actual_width, actual_height, width_, height_);
    }
    std::stringstream ss;'''
assert original.count(anchor) == 1
control = original.replace(anchor, diagnostic)
anchor = '    width_ = cur_properties.width;\n    height_ = cur_properties.height;'
replacement = '''    const bool fixed_validation_size = offscreen_ && Options::validate && width > 0 && height > 0;
    width_ = fixed_validation_size ? width : cur_properties.width;
    height_ = fixed_validation_size ? height : cur_properties.height;'''
assert control.count(anchor) == 1
fixed = control.replace(anchor, replacement)
(build / 'fbo-size-only.patch').write_text(''.join(difflib.unified_diff(control.splitlines(True), fixed.splitlines(True), fromfile='control/canvas-generic.cpp', tofile='fixed/canvas-generic.cpp')))
libs = ['/usr/lib/libjpeg.so.8', '/usr/lib/libpng16.so.16',
        '/usr/lib/libwayland-client.so.0', '/usr/lib/libwayland-cursor.so.0',
        '/usr/lib/libwayland-egl.so.1', '-L/usr/lib', '-Wl,-rpath-link,/usr/lib:/lib', '-lm', '-ldl']
receipts = []
for variant, body in [('control', control), ('fixed', fixed)]:
    source = build / ('canvas-' + variant + '.cpp')
    source.write_text(body)
    obj = build / ('canvas-' + variant + '.o')
    command([cxx] + base + ['-std=c++14', '-c', str(source), '-o', str(obj)])
    binary = build / ('glmark2-es2-wayland-' + variant)
    command([cxx, '--sysroot=' + str(sdk), '-B' + str(sdk / 'usr/bin')] + objects + [str(obj)] + libs + ['-o', str(binary)])
    receipts.append({'variant': variant, 'bytes': binary.stat().st_size,
                     'sha256': hashlib.sha256(binary.read_bytes()).hexdigest()})
(build / 'build-receipts.json').write_text(json.dumps(receipts, indent=2) + '\n')
print('BOTH_NATIVE_TOOLS_BUILT', round(time.monotonic() - start, 1), flush=True)
