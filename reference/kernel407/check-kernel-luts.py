"""Pass generated nonzero curves through the maintained typed kernel encoder."""
from pathlib import Path
import ctypes, hashlib, importlib.util, json, struct, subprocess
import host
HERE = Path(__file__).resolve().parent
P = host.PRIVATE
spec = importlib.util.spec_from_file_location('storage284', HERE.parent / 'kernel284/storage.py')
storage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(storage)
source = storage.mounted_build().parent / 'source354'
directory = source / 'drivers/media/platform/qcom/camss'
model = P.parent / 'kernel405'
assert (model / 'colour.c').read_bytes() == (directory / 'camss-icp-a5-colour.c').read_bytes()
assert (model / 'include/camss-icp-a5-colour.h').read_bytes() == (directory / 'camss-icp-a5-colour.h').read_bytes()
q = subprocess.run(['gcc', '-shared', '-fPIC', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
                    '-I' + str(model / 'include'), str(model / 'colour.c'), str(model / 'bypass.c'),
                    '-o', str(P / 'current-colour-codec.so')], capture_output=True)
(P / 'kernel-codec-build.log').write_bytes(q.stdout + q.stderr)
assert not q.returncode, q.stderr.decode()
lib = ctypes.CDLL(str(P / 'current-colour-codec.so'))
encode = lib.camss_a5_ipe_encode_ltm_iq
encode.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
encode.restype = ctypes.c_int
check = lib.camss_a5_ipe_ltm_check
check.argtypes = [ctypes.c_void_p]
check.restype = ctypes.c_int
validation = json.loads((HERE / 'curves-validation.json').read_text())
assert validation['passed']
count = validation['valid_cases']
raw = (P / 'curves-host-output-private.bin').read_bytes()
expected = (P / 'curve-source-expected-private.bin').read_bytes()
different = 0
nonzero = 0
for i in range(count):
    words = struct.unpack_from('<96I', raw, i * 788 + 404)
    signed = []
    for word in words:
        base, delta = word & 4095, (word >> 12) & 4095
        signed.append((base - 4096 if base & 2048 else base,
                       delta - 4096 if delta & 2048 else delta))
    typed = bytearray(2800)
    # Only IP is enabled; this check concerns typed segment ownership/layout,
    # not hardware defaults or the remaining IQ controls and table families.
    struct.pack_into('<I', typed, 84, 1)
    for j, (base, delta) in enumerate(signed[:64]):
        struct.pack_into('<hh', typed, 880 + j * 4, base, delta)
    for j, (base, delta) in enumerate(signed[64:]):
        struct.pack_into('<hh', typed, 1392 + j * 4, base, delta)
    request = ctypes.create_string_buffer(bytes(typed))
    assert not check(request)
    output = ctypes.create_string_buffer(bytes([0xa7]) * 9008)
    assert not encode(output, 9008, 0x07802000, None, None, request)
    assert request.raw[:2800] == typed
    assert output.raw[8944:9008] == bytes([0xa7]) * 64
    actual = output.raw[7024:7280] + output.raw[7536:7664]
    wanted = expected[i * 788 + 404:(i + 1) * 788]
    different += sum(a != b for a, b in zip(actual, wanted))
    nonzero += bool(any(words))
assert not different
report = dict(stage=407, cases=count, nonzero_table_cases=nonzero,
              source_commit=json.loads((HERE / 'source-state.json').read_text())['commit'],
              compiled_colour_source_matches_maintained_kernel=True,
              typed_request_bytes=2800, iq_bytes=8944,
              float_math_to_quantized_signed_segments_to_native_lut=True,
              scale64_lce16_each=True, compared_bytes=count * 384,
              different_bytes=different, all_requests_valid=True,
              typed_input_and_output_tail_unchanged=True,
              other_luts_and_iq_not_claimed_as_factory_generated=True,
              hardware_submission_not_performed=True, phone_accessed=False, passed=True)
(HERE / 'kernel-luts-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
