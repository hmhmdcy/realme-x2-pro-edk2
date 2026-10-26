from hashlib import sha256
from pathlib import Path

root = Path(__file__).resolve().parent
original = root.parent / 'rx53/eud-usb-overlap-pipelined.py'
assert sha256(original.read_bytes()).hexdigest() == 'd3d68d5f7f4b72fff48f3fa1efc6369562d375f1e0b4ffb4291fe524a6503454'
source = original.read_text()
def replace(old,new):
    global source
    assert source.count(old) == 1, (old,source.count(old))
    source = source.replace(old,new)
replace('overlap manually triggers one RX51 kmsg record and one delayed native probe.',
        'overlap manually triggers one unchanged RX51 kmsg record and one F1 header.\nA single F1 [90 02] is submitted during that record, never as tty LEN2.')
replace('overlap_marker_at=None, overlap_end_at=None, overlap_receipt=None,',
        'overlap_marker_at=None, overlap_end_at=None, overlap_receipt=None,\n                 f1_submitted=False, f1_disconnect=None, f1_console_receipt=False,')
replace("overlap_delay_ms=152, overlap_probe_hex='523531483d310a',",
        "overlap_delay_ms=152, overlap_f1_hex='90 02',")
replace("except Exception as error:\n                    failed('io-reader', error)",
        "except usb.core.USBError as error:\n                    if state['f1_submitted'] and error.errno in (5,19):\n                        with changed:\n                            state['f1_disconnect'] = repr(error)\n                            changed.notify_all()\n                        event('disconnect_after_f1', error=repr(error), errno=error.errno)\n                    else:\n                        failed('io-reader', error)\n                except Exception as error:\n                    failed('io-reader', error)")
replace("state['overlap_receipt'] = send(b'R51H=1\\n', gap=False)\n                    state['overlap_armed'] = False\n                    if not state['overlap_receipt']:\n                        state['synchronized'] = False\n                        event('overlap_timeout_capture_only', automatic_out=False)\n                        print('Probe stopped without retry. Capture remains open; manual u required before any new command.', flush=True)",
        "state['f1_submitted'] = True\n                    event('f1_out_submit', hex='90 02', attempt=1, payload_bytes=0)\n                    actual = dev.write(epout, bytes([0x90,2]), timeout=500)\n                    event('f1_out_complete', length=actual)\n                    if actual != 2:\n                        raise RuntimeError('Short F1 OUT; do not retry')\n                    deadline = time.monotonic()+12\n                    with changed:\n                        while not state['f1_disconnect']:\n                            if errors:\n                                raise RuntimeError(errors)\n                            remaining = deadline-time.monotonic()\n                            if remaining <= 0:\n                                break\n                            changed.wait(timeout=min(remaining,.1))\n                        state['f1_console_receipt'] = 'eud: RX46 F1 via=console ' in state['text'][state['overlap_boundary']:]\n                    event('f1_observation', console_receipt=state['f1_console_receipt'], disconnect=state['f1_disconnect'], physical_fastboot_check_required=True)\n                    state['overlap_armed'] = False\n                    break")
target = root/'eud-usb-console-f1.py'
assert not target.exists()
target.write_bytes(source.encode())
(root/'bootstrap-f1.sh').write_text('set -euo pipefail\nmodprobe usbmon\nexec python3 /mnt/e/edk2-samurai-out/rx54/eud-usb-console-f1.py --out /mnt/e/edk2-samurai-out/rx54/console-f1-01 --seconds 180\n')
hash_value = sha256(target.read_bytes()).hexdigest()
wrapper = (root/'capture-repeat.ps1').read_text().replace('eud-usb-repeated-console','eud-usb-console-f1').replace('48bad103de1b41705d194ad332d88038807f3724753379af3d233d6fc6fa74ce', hash_value).replace('before-state.json','before-f1-state.json').replace('bootstrap-repeat.sh','bootstrap-f1.sh')
(root/'capture-f1.ps1').write_bytes(wrapper.encode())
print(hash_value, target)
