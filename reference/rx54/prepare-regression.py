from hashlib import sha256
from pathlib import Path

root = Path(__file__).resolve().parent
original = root.parent / 'rx53/eud-usb-overlap-pipelined.py'
assert sha256(original.read_bytes()).hexdigest() == 'd3d68d5f7f4b72fff48f3fa1efc6369562d375f1e0b4ffb4291fe524a6503454'
source = original.read_text()

def replace(old, new):
    global source
    assert source.count(old) == 1, (old, source.count(old))
    source = source.replace(old, new)

replace('overlap manually triggers one RX51 kmsg record and one delayed native probe.',
        'overlap manually triggers one unchanged RX51 kmsg record per step, up to nine.\nEach step submits a different R54H01..09 assignment once; no automatic loop.')
replace('overlap_used=False, overlap_armed=False, overlap_boundary=0,',
        'overlap_runs=0, overlap_armed=False, overlap_boundary=0,')
replace('max_manual_steps=12,', 'max_manual_steps=18,')
replace("overlap_delay_ms=152, overlap_probe_hex='523531483d310a',",
        "overlap_delay_ms=152, max_overlaps=9, overlap_probe_pattern='R54H%02d=1\\n',")
replace("print('\\nCOMMAND> u | send COMMAND | overlap | drain | x; one owner, no automatic retries', flush=True)",
        "print('\\nCOMMAND> u | send COMMAND | overlap (max 9 manual steps) | drain | x; no automatic retries', flush=True)")
replace("while time.monotonic() - started < args.seconds and state['steps'] < 12:",
        "while time.monotonic() - started < args.seconds and state['steps'] < 18:")
replace("if not state['synchronized'] or state['overlap_used']:\n                        raise RuntimeError('Overlap needs fresh sync and can run only once')",
        "if not state['synchronized'] or state['overlap_runs'] >= 9:\n                        raise RuntimeError('Overlap needs fresh sync and permits at most nine manual steps')")
replace("state['overlap_used'] = state['overlap_armed'] = True\n                        state['overlap_boundary'] = len(state['text'])",
        "state['overlap_runs'] += 1\n                        state['overlap_armed'] = True\n                        state['overlap_boundary'] = len(state['text'])\n                        state['overlap_marker_at'] = state['overlap_end_at'] = state['overlap_receipt'] = None")
replace("event('overlap_armed', command=command, bytes=len(payload), delay_ms=152)",
        "event('overlap_armed', index=state['overlap_runs'], command=command, bytes=len(payload), delay_ms=152)")
replace("state['overlap_receipt'] = send(b'R51H=1\\n', gap=False)",
        "probe = ('R54H%02d=1\\n' % state['overlap_runs']).encode('ascii')\n                    state['overlap_receipt'] = send(probe, gap=False)")

target = root / 'eud-usb-repeated-console.py'
assert not target.exists()
target.write_bytes(source.encode('utf-8'))
(root / 'bootstrap-repeat.sh').write_text('set -euo pipefail\nmodprobe usbmon\nexec python3 /mnt/e/edk2-samurai-out/rx54/eud-usb-repeated-console.py --out /mnt/e/edk2-samurai-out/rx54/repeated-console-01 --seconds 600\n')
print(sha256(target.read_bytes()).hexdigest(), target)
