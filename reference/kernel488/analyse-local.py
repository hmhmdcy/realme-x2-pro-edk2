"""Guarded, offline one-file candidate and native source-function validation."""
from pathlib import Path
import argparse
import difflib
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import traceback

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel488')
RELATIVE = Path('src/libcamera/v4l2_subdevice.cpp')
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()


def block(text, start):
    begin = text.index(start)
    brace = text.index('{', begin)
    depth = 1
    end = brace + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[begin:end]


def save_new(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        assert path.read_bytes() == content, ('Preserve existing material', str(path))
    else:
        path.write_bytes(content)


def run(command, directory, label, **kwargs):
    result = subprocess.run(command, capture_output=True, **kwargs)
    (directory / (label + '-stdout-private.bin')).write_bytes(result.stdout)
    (directory / (label + '-stderr-private.bin')).write_bytes(result.stderr)
    (directory / (label + '-result-private.json')).write_text(json.dumps(dict(argv=command, exit_code=result.returncode), indent=2) + '\n')
    assert result.returncode == 0, (label, result.stderr.decode(errors='replace')[-3000:])
    return result


def harness(tree, subdevice):
    formats = (tree / 'include/libcamera/internal/formats.h').read_text()
    info_header = (tree / 'include/libcamera/internal/v4l2_subdevice.h').read_text()
    conversion = (tree / 'src/libcamera/v4l2_device.cpp').read_text()
    spaces = (tree / 'src/libcamera/color_space.cpp').read_text()
    encoding = block(formats, 'enum ColourEncoding') + ';'
    info = block(info_header, 'class MediaBusFormatInfo') + ';'
    table = block(subdevice, 'const std::map<uint32_t, MediaBusFormatInfo>') + ';'
    constants = '\n'.join(block(spaces, 'const ColorSpace ColorSpace::' + name) + ';'
                          for name in ['Raw', 'Srgb', 'Sycc', 'Smpte170m', 'Rec709', 'Rec2020'])
    maps = '\n'.join(block(conversion, 'static const std::map<uint32_t, ' + kind + '> ' + name) + ';'
                     for kind, name in [('ColorSpace', 'v4l2ToColorSpace'),
                         ('ColorSpace::TransferFunction', 'v4l2ToTransferFunction'),
                         ('ColorSpace::YcbcrEncoding', 'v4l2ToYcbcrEncoding'), ('ColorSpace::Range', 'v4l2ToRange')])
    convert = block(conversion, 'template<typename T>\nstd::optional<ColorSpace> V4L2Device::toColorSpace')
    lookup = block(subdevice, 'const MediaBusFormatInfo &MediaBusFormatInfo::info')
    sub_convert = block(subdevice, 'std::optional<ColorSpace> V4L2Subdevice::toColorSpace')
    prefix = '''#include <cstdint>
#include <map>
#include <tuple>
#include <linux/media-bus-format.h>
#include <linux/videodev2.h>
#include <linux/v4l2-subdev.h>
#include <libcamera/color_space.h>
namespace libcamera {
int warnings = 0;
struct LogSink { template<typename T> LogSink &operator<<(const T &) { return *this; } };
#define LOG(category, level) (++warnings, LogSink{})
namespace utils { inline uint32_t hex(uint32_t value, unsigned int) { return value; } }
class PixelFormatInfo { public: ENCODING };
INFO
class V4L2Device { public:
template<typename T> static std::optional<ColorSpace> toColorSpace(const T &, PixelFormatInfo::ColourEncoding);
};
class V4L2Subdevice { public: std::optional<ColorSpace> toColorSpace(const v4l2_mbus_framefmt &) const; };
'''.replace('ENCODING', encoding).replace('INFO', info)
    return prefix + '\n'.join([constants, table, maps, lookup, convert, sub_convert]) + '\n}\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--output', type=Path, default=HERE / 'validation.json')
    args = parser.parse_args()
    assert re.fullmatch(r'r[1-9][0-9]*', args.run_id)
    spec = importlib.util.spec_from_file_location('storage488', HERE.parent / 'kernel461/storage.py')
    storage = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(storage)
    volume = storage.mount.mounted_build().parent  # Before every ext4 source access.
    tree = volume / 'libcamera473-processed-manager-capacity/src/libcamera-v0.7.2'
    kernel = volume / 'source354'
    directory = PRIVATE / ('software-' + args.run_id)
    directory.mkdir(parents=True, exist_ok=False)
    try:
        authorities = [tree / RELATIVE, tree / 'src/libcamera/v4l2_device.cpp', tree / 'src/libcamera/color_space.cpp',
            tree / 'include/libcamera/color_space.h', tree / 'include/libcamera/internal/formats.h',
            tree / 'include/libcamera/internal/v4l2_subdevice.h', tree / 'include/linux/media-bus-format.h',
            tree / 'src/libcamera/pipeline/camss-vfe/camss_vfe.cpp', kernel / 'include/uapi/linux/media-bus-format.h',
            kernel / 'Documentation/userspace-api/media/v4l/subdev-formats.rst',
            kernel / 'drivers/media/platform/qcom/camss/camss-vfe.c', kernel / 'drivers/media/platform/qcom/camss/camss-vfe-175-ds4.c']
        before = {str(path): sha(path) for path in authorities}
        recorded = json.loads((HERE.parent / 'kernel441/kernel-source-state.json').read_bytes())
        for row in recorded['source_hashes']:
            assert sha(kernel / row['path']) == row['sha256'], row['path']
        recorded = json.loads((HERE.parent / 'kernel473/source-state.json').read_bytes())
        for row in recorded['source_hashes']:
            assert sha(tree / row['path']) == row['sha256'], row['path']
        for header in [tree / 'include/linux/media-bus-format.h', kernel / 'include/uapi/linux/media-bus-format.h']:
            assert re.search(r'#define MEDIA_BUS_FMT_UYYVYY10_0_5X30\s+0x2027', header.read_text())
        ds4 = (kernel / 'drivers/media/platform/qcom/camss/camss-vfe-175-ds4.c').read_text()
        assert '{ MEDIA_BUS_FMT_UYYVYY10_0_5X30, 15, V4L2_PIX_FMT_QCOM_PD10_LOCAL' in ds4
        baseline = (tree / RELATIVE).read_text()
        assert '{ MEDIA_BUS_FMT_UYYVYY10_0_5X30,' not in baseline
        anchor = '\t{ MEDIA_BUS_FMT_YUV10_1X30, {'
        end = baseline.index('\n\t} },', baseline.index(anchor)) + len('\n\t} },')
        addition = '''
\t{ MEDIA_BUS_FMT_UYYVYY10_0_5X30, {
\t\t.name = "UYYVYY10_0_5X30",
\t\t.code = MEDIA_BUS_FMT_UYYVYY10_0_5X30,
\t\t.type = MediaBusFormatInfo::Type::Image,
\t\t.bitsPerPixel = 15,
\t\t.colourEncoding = PixelFormatInfo::ColourEncodingYUV,
\t} },'''
        candidate = baseline[:end] + addition + baseline[end:]
        assert candidate.replace(addition, '', 1) == baseline
        save_new(PRIVATE / 'baseline' / RELATIVE, baseline.encode())
        save_new(PRIVATE / 'candidate' / RELATIVE, candidate.encode())
        patch = ''.join(difflib.unified_diff(baseline.splitlines(keepends=True), candidate.splitlines(keepends=True),
                    fromfile='a/' + RELATIVE.as_posix(), tofile='b/' + RELATIVE.as_posix()))
        patch_path = HERE / '0001-v4l2-recognize-uyyvyy10-0-5x30.patch'
        save_new(patch_path, patch.encode())
        replay = directory / 'replay'
        save_new(replay / RELATIVE, baseline.encode())
        result = run(['patch', '--batch', '--fuzz=0', '-p1', '-d', str(replay), '-i', str(patch_path)], directory, 'patch')
        assert b'offset' not in result.stdout and b'fuzz' not in result.stdout
        assert (replay / RELATIVE).read_text() == candidate
        source_result = dict(stage=488, passed=True, baseline_source=before, source473_and_kernel441_hashes_match=True,
            only_changed_path=RELATIVE.as_posix(), added_lines=7, baseline_sha256=hashlib.sha256(baseline.encode()).hexdigest(),
            candidate_sha256=hashlib.sha256(candidate.encode()).hexdigest(), patch_sha256=sha(patch_path),
            one_file_candidate=True, zero_fuzz_zero_offset=True, original_sources_preserved=True, sdk_accessed=False,
            header_or_driver_or_pd10_memory_layout_changed=False, hardware_validated=False, installed=False)
        save_new(HERE / 'source-validation.json', (json.dumps(source_result, indent=2) + '\n').encode())
        compiler = shutil.which('g++')
        assert compiler == '/usr/bin/g++', 'Use the native host compiler, never the SDK'
        checks = []
        for mode, source in [('baseline', baseline), ('candidate', candidate)]:
            work = directory / mode
            work.mkdir()
            (work / 'source-under-test.inc').write_text(harness(tree, source))
            (work / 'test.cpp').write_bytes((HERE / 'colour-space-test.cpp').read_bytes())
            binary = work / 'colour-space-test'
            run([compiler, '-std=c++20', '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined',
                 '-fno-omit-frame-pointer', '-g', '-I', str(tree / 'include'), str(work / 'test.cpp'), '-o', str(binary)], directory, mode + '-compile')
            result = run([str(binary), mode], directory, mode + '-run')
            assert b'passed=1' in result.stdout
            checks.append(dict(mode=mode, result=result.stdout.decode().strip(), binary_sha256=sha(binary),
                extracted_source_sha256=sha(work / 'source-under-test.inc')))
        assert {str(path): sha(path) for path in authorities} == before
        result = dict(stage=488, passed=True, scope='offline source-function checks, not full libcamera or hardware execution',
            native_compiler=compiler, sanitizer='address,undefined', production_table_lookup_and_conversion_bodies_extracted=True,
            device_shells_and_logging_stubbed=True, original_headers_and_colorspace_constants_used=True, software_checks=checks,
            current_0x2027_meaning='UYYVYY10_0_5X30 YUV, average15 bits/pixel; bus width30 is not bpp',
            existing_defaults_can_coincide_despite_rgb_fallback=True, explicit_ycbcr_and_limited_range_preserved_after_fix=True,
            unknown_codes_still_warn_and_fall_back=True, invalid_color_fields_still_unset=True,
            nv12_sycc_pipeline_policy_unchanged=True,
            pd10_bus_description_not_memory_layout=True, phone_accessed=False, ssh_accessed=False, sdk_accessed=False,
            full_libcamera_build=False, hardware_validated=False, installed=False, source_validation_sha256=sha(HERE / 'source-validation.json'),
            test_source_sha256=sha(HERE / 'colour-space-test.cpp'), analyser_sha256=sha(__file__))
        output = args.output
        assert not output.exists()
        output.write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=2))
    except BaseException:
        (directory / 'failure-private.txt').write_text(traceback.format_exc())
        raise


if __name__ == '__main__':
    main()
