"""Validate the original S5K3M5 gain calculation without executing vendor code."""
from pathlib import Path
import hashlib, json, struct, subprocess
import host

R = Path(__file__).resolve().parent
p = host.PRIVATE.parent / 'kernel115/vendor-camera-modules/com.qti.sensor.s5k3m5sx.so'
raw = p.read_bytes()
expected = {
    0x1024: 0x1e2e1001,  # minimum 1.0
    0x102c: 0x1e261002,  # maximum 16.0
    0x1054: 0x1e59ec68,  # convert unsigned fixed point with five fractional bits
    0x1058: 0x52804009,  # register ceiling 512
    0x1064: 0x7108011f,  # compare against 512
    0x1070: 0xd2e7f409,  # double constant 1/32
    0x1084: 0x1e650886,  # multiply code by 1/32
}
for offset, value in expected.items():
    assert struct.unpack_from('<I', raw, offset)[0] == value, hex(offset)
q = subprocess.run(['aarch64-linux-gnu-objdump', '-d', str(p)], capture_output=True, timeout=20, check=True)
(host.PRIVATE / 'factory-s5k3m5-disassembly-private.txt').write_bytes(q.stdout)
report = dict(stage=271, binary_sha256=hashlib.sha256(raw).hexdigest(),
              factory_library_not_executed=True, original_binary_unchanged=hashlib.sha256(p.read_bytes()).digest() == hashlib.sha256(raw).digest(),
              analogue_gain_min=1, analogue_gain_max=16, register_code_min=32, register_code_max=512,
              register_gain_formula='floor(clamp(real_gain,1,16)*32)', real_gain_formula='register_code/32',
              register_gain_step=0.03125, current_kernel_userspace_step=1,
              addresses_checked=[hex(x) for x in expected], physical_response_pending=True)
(R / 'factory-gain-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
