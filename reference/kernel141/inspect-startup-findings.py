from pathlib import Path
import json
import re
import tarfile

out = Path('/mnt/e/edk2-samurai-out/kernel141')
with tarfile.open(out / 'reboot140-startup-private.tar.gz') as archive:
    data = {m.name.removeprefix('./'): archive.extractfile(m).read() for m in archive if m.isfile()}
text = data['dmesg-final-private.txt'].decode()
for line in text.splitlines():
    if any(token in line for token in ['TX DMA diagnostic', 'NGD suspend rejected', 'BAM DMA diagnostic',
                                      'unable to prepare channel', 'frame done timeout', 'buffer unavailable', 'tx timeout']):
        print(re.sub(r'\b(?:0x)?[0-9a-f]{8,16}\b', '[redacted]', line))
print('NGD_STARTUP_CONTEXT')
for line in text.splitlines():
    match = re.match(r'\[\s*(\d+\.\d+)\]', line)
    if match and 20 <= float(match.group(1)) <= 32 and re.search(r'slim|ngd|wcd|adsp|PDR|SSR', line, re.I):
        print(re.sub(r'\b(?:0x)?[0-9a-f]{8,16}\b', '[redacted]', line))
events = json.loads((out / 'parsed-startup-events-private.json').read_text())
for timeout in [e for e in events if e['name'] == 'dpu_enc_frame_done_timeout']:
    stamp = timeout['seconds']
    arm = next(e for e in reversed(events) if e['seconds'] < stamp and e['name'] == 'dpu_enc_frame_watchdog' and 'action=arm ' in e['body'])
    relevant = [e for e in events if arm['seconds'] - 0.001 <= e['seconds'] <= stamp + 0.001
                and (e['name'] in ['dpu_enc_frame_watchdog', 'dpu_enc_frame_done_timeout', 'dpu_enc_frame_done_cb',
                                  'dpu_enc_phys_cmd_pp_tx_done', 'dpu_crtc_vblank_cb', 'dpu_enc_kickoff',
                                  'dpu_enc_trigger_start', 'dpu_enc_rc', 'msm_atomic_commit_tail_finish']
                     or e['name'] == 'dpu_enc_irq_wait_success')]
    print('TIMEOUT_TARGET', stamp, 'ARM_TO_EXPIRE_MS', round((stamp - arm['seconds']) * 1000, 3))
    for e in relevant:
        print(round((e['seconds'] - stamp) * 1000, 3), e['name'], re.sub(r'\b(?:0x)?[0-9a-f]{8,16}\b', '[redacted]', e['body']))
    before = [e for e in events if arm['seconds'] <= e['seconds'] <= stamp]
    from collections import Counter
    print('EVENTS_DURING_WAIT', dict(Counter(e['name'] for e in before)))
lines = data['startup-trace-private.txt'].decode().splitlines()
for timeout in [e for e in events if e['name'] == 'dpu_enc_frame_done_timeout']:
    selected = []
    for line in lines:
        match = re.search(r'\[(\d+)\].*?\s(\d+\.\d+):\s+([a-zA-Z0-9_]+):', line)
        if match and timeout['seconds'] - 0.096 <= float(match.group(2)) <= timeout['seconds'] + 0.0003:
            selected.append(dict(cpu=int(match.group(1)), seconds=float(match.group(2)), event=match.group(3)))
    print('CPU_EVENT_GAP', json.dumps(selected[-30:]))
