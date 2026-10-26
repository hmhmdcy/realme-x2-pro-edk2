"""Finite native source-path oracle plus ARM64 core install-byte validation.

Reads the existing guarded source tree. Builds a tiny native DSO, never the SDK
or production library. Its source_paths.cpp is compiled without modification.
The resulting ARM64 core copy is not installed or executed by this check.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def exact_function(text, signature):
    start = text.index(signature)
    brace = text.index('{', start)
    depth = 0
    for end in range(brace, len(text)):
        if text[end] == '{':
            depth += 1
        elif text[end] == '}':
            depth -= 1
            if depth == 0:
                return text[start:end + 1]
    raise AssertionError('Unclosed source function')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--private', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    args = parser.parse_args()
    assert not args.private.exists(), 'Use a fresh attempt directory'
    guard = load('guard485', ROOT / 'reference/kernel461/storage.py')
    guard.mount.mounted_build()
    source = Path(json.loads((ROOT / 'reference/kernel473/source-state.json').read_bytes())['source'])
    relevant = ['src/libcamera/source_paths.cpp', 'src/libcamera/base/utils.cpp',
                'src/libcamera/meson.build', 'include/libcamera/internal/source_paths.h',
                'include/libcamera/base/utils.h', 'include/libcamera/base/class.h',
                'include/libcamera/base/private.h']
    originals = {name: sha256(source / name) for name in relevant}
    normalizer = load('normalize485', HERE / 'normalize-core.py')
    args.private.mkdir(parents=True)
    build = args.private / 'build'
    native = build / 'src/libcamera/source_paths_oracle.so'
    native.parent.mkdir(parents=True)
    (build / 'source').symlink_to(source, target_is_directory=True)
    dirname = exact_function((source / relevant[1]).read_text(),
                             'std::string dirname(const std::string &path)')
    bridge = args.private / 'bridge.cpp'
    bridge.write_text('#include <libcamera/base/utils.h>\n'
                      '#include "libcamera/internal/source_paths.h"\n'
                      'namespace libcamera { namespace utils {\n' + dirname + '\n}}\n'
                      'extern "C" const char *oracle_build() {\n'
                      ' static thread_local std::string s;\n'
                      ' s = libcamera::utils::libcameraBuildPath(); return s.c_str(); }\n'
                      'extern "C" const char *oracle_source() {\n'
                      ' static thread_local std::string s;\n'
                      ' s = libcamera::utils::libcameraSourcePath(); return s.c_str(); }\n')
    compile_command = ['g++', '-std=c++20', '-Wall', '-Wextra', '-Werror',
                       '-fPIC', '-shared', '-DLIBCAMERA_BASE_PRIVATE',
                       '-I' + str(source / 'include'), str(source / relevant[0]),
                       str(bridge), '-Wl,-rpath,/', '-ldl', '-o', str(native)]
    result = subprocess.run(compile_command, capture_output=True, timeout=45)
    (args.private / 'compile.log').write_bytes(result.stdout + result.stderr)
    assert result.returncode == 0, (result.stdout + result.stderr).decode()
    misplaced = args.private / 'misplaced/usr/lib/source_paths_oracle.so'
    misplaced.parent.mkdir(parents=True)
    import shutil
    shutil.copy2(native, misplaced)
    installed = misplaced.parent / 'source_paths_oracle_installed.so'
    native_delta = normalizer.normalize(misplaced, installed, sha256(misplaced), b'/', machine=62)
    code = ('import ctypes,json,sys; d=ctypes.CDLL(sys.argv[1]); '
            'd.oracle_build.restype=ctypes.c_char_p; d.oracle_source.restype=ctypes.c_char_p; '
            'print(json.dumps({"build":d.oracle_build().decode(),'
            '"source":d.oracle_source().decode()}))')
    cases = []
    for label, path, expected in [
        ('uninstalled-build', native, {'build': str(build.resolve()) + '/', 'source': str(source.resolve()) + '/'}),
        ('copied-with-build-runpath', misplaced, {'build': str((args.private / 'misplaced').resolve()) + '/', 'source': ''}),
        ('meson-installed-copy', installed, {'build': '', 'source': ''}),
    ]:
        result = subprocess.run([sys.executable, '-B', '-c', code, str(path)],
                                capture_output=True, text=True, timeout=15)
        (args.private / (label + '.log')).write_text(result.stdout + result.stderr)
        assert result.returncode == 0, result.stderr
        actual = json.loads(result.stdout)
        assert actual == expected, (label, actual, expected)
        cases.append({'case': label, 'passed': True,
                      'build_path_empty': not actual['build'],
                      'source_path_empty': not actual['source']})
    input_core = Path('/mnt/e/edk2-samurai-out/kernel473/libcamera.so.0.7.2')
    output_core = args.private / 'libcamera.so.0.7.2'
    arm_delta = normalizer.normalize(input_core, output_core,
        'a21fcedde2f591f809a9c388a9a6ab78fa5072f33e06c91bbd55c8abf34cd97b', b'$ORIGIN/base:/')
    assert originals == {name: sha256(source / name) for name in relevant}
    receipt = {
        'stage': 485, 'passed': True,
        'native_actual_source_paths_cpp_compiled_unmodified': True,
        'dirname_function_extracted_verbatim': True,
        'source_hashes': originals,
        'native_cases': cases, 'native_install_delta': native_delta,
        'arm64_core_install_delta': arm_delta,
        'production_source_changed': False, 'original_core_changed': False,
        'ipa_proxy_signature_changed': False,
        'sdk_used': False, 'phone_accessed': False,
        'arm64_candidate_executed': False, 'installed': False,
        'real_system_ipa_config_worker_lookup_verified': False,
        'real_ipa_signature_verification_with_candidate': False,
    }
    args.receipt.write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
