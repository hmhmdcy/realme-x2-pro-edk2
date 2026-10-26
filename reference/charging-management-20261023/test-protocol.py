"""Replay privately retained real packets and reject bit corruptions/errors."""
from pathlib import Path
import hashlib
import json
import subprocess

ref = Path(__file__).resolve().parent
private = Path('/mnt/e/edk2-samurai-out/charging-management-20261023/window2')
capture = json.loads((private / 'fixed-query-private.json').read_text())
fixture = private / 'packets-private.bin'
fixture.write_bytes(b''.join(int(k, 16).to_bytes(2, 'little') + bytes.fromhex(capture['gauge'][k]['raw_hex'])
    for k in ['0x1', '0x51', '0x53', '0x54', '0x57', '0x71']))
binary = Path('/home/cy122/charging-management-20261023/test-protocol')
cmd = ['gcc', '-std=c11', '-g', '-Wall', '-Wextra', '-Werror',
       '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
       '-I' + str(ref), str(ref / 'test-protocol.c'), '-o', str(binary)]
subprocess.run(cmd, check=True)
q = subprocess.run([str(binary), str(fixture)], capture_output=True, text=True)
print(q.stdout, end=''); print(q.stderr, end=''); q.check_returncode()
result = json.loads(q.stdout)
result['tested_files'] = {n: hashlib.sha256((ref / n).read_bytes()).hexdigest()
    for n in ['gauge-protocol.h', 'samurai-usb-input-decode.h', 'test-protocol.c']}
result['real_fixture_sha256'] = hashlib.sha256(fixture.read_bytes()).hexdigest()
result['sanitizers'] = ['ASan', 'UBSan']
(ref / 'protocol-test-result.json').write_text(json.dumps(result, indent=2) + '\n')
