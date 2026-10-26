"""Inspect target temporal block and bounded pinned parameter declarations."""
from pathlib import Path
import hashlib, importlib.util, json, struct, subprocess
import host
HERE = Path(__file__).resolve().parent
P = host.PRIVATE
spec = importlib.util.spec_from_file_location('storage284', HERE.parent / 'kernel284/storage.py')
storage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(storage)
source = storage.mounted_build().parent / 'source354'
state = json.loads((HERE.parent / 'kernel407/source-state.json').read_text())
assert subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip() == state['commit']
assert not subprocess.check_output(['git', '-C', str(source), 'status', '--porcelain'])
state.update(stage=408, source_unchanged_from407=True, phone_accessed=False,
             new_hardware_verification=False, last_device_evidence_stage=406,
             new_temporal_math_pending=True)
(HERE / 'source-state.json').write_text(json.dumps(state, indent=2) + '\n')
hal = P.parent / 'kernel281/camera.qcom.so-private'
for name, start, end in [('temporal-private.asm', 0x360560, 0x360ac8),
                         ('temporal-inputs-private.asm', 0x35ea60, 0x35ea94)]:
    q = subprocess.run(['aarch64-linux-gnu-objdump', '-d', '--start-address=' + hex(start),
                        '--stop-address=' + hex(end), str(hal)], capture_output=True, check=True)
    (P / name).write_bytes(q.stdout)
raw = hal.read_bytes()
phoff = struct.unpack_from('<Q', raw, 32)[0]
stride, count = struct.unpack_from('<HH', raw, 54)
segments = [struct.unpack_from('<II6Q', raw, phoff + i * stride) for i in range(count)]
def read(va, size):
    item = next(s for s in segments if s[0] == 1 and s[3] <= va and va + size <= s[3] + s[5])
    return raw[item[2] + va - item[3]:item[2] + va - item[3] + size]
print('target temporal log:', read(0x8e028, 256).split(b'\0')[0].decode())
repo = '/home/cy122/x2pro-linux/refs/CamxChi-k117'
rev = '9f17f1b568626b393e785b369c5dc94543774d7a'
paths = ['camx/src/core/hal/camxhal3types.h', 'camx/src/hwl/ispiqmodule/camxispiqmodule.h',
         'chi-cdk/api/stats/chistatsproperty.h']
out = P / 'sources'
out.mkdir(exist_ok=True)
rows = []
for name in paths:
    data = subprocess.check_output(['git', '-C', repo, 'show', rev + ':' + name], timeout=45)
    target = out / Path(name).name
    target.write_bytes(data)
    rows.append(dict(path=name, bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                     url='https://github.com/bjzhou/CamxChi/blob/' + rev + '/' + name))
    lines = data.decode().splitlines()
    for i, line in enumerate(lines):
        if any(word in line for word in ['HALTagsData', 'struct ISPInputData', 'ltmStrength', 'ltmContrast']):
            print(name, i+1, '\n'.join(lines[max(0, i-2):i+55]))
(HERE / 'primary-sources.json').write_text(json.dumps(dict(stage=408, commit=rev, files=rows), indent=2) + '\n')
print(json.dumps(dict(stage=408, source_clean_and_unchanged=True, phone_accessed=False)))
