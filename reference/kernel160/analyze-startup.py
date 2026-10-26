from pathlib import Path
import hashlib, json, re, tarfile

ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel160')
out = Path('/mnt/e/edk2-samurai-out/kernel160')
with tarfile.open(out / 'first-evidence-private.tar.gz') as archive:
    read = lambda name: archive.extractfile('k160-' + name).read().decode()
    log = read('first-runtime/dmesg-private.txt')
    early = read('first-startup/early-trace-private.txt')
    stats = json.loads(read('first-startup/early-stats.json'))
    ready = json.loads(read('first-startup/ready.json'))
    assert log.index('DSI firmware stop before PHY: CTRL=0x1f5 -> 0x0') < log.index('boot CTL0:') < log.index('boot CTL0 cleared:')
    assert log.count('DSI firmware stop before PHY:') == 1
    events = []
    for line in early.splitlines():
        match = re.search(r'(\d+\.\d+): (dpu_first_frame_backlight|drm_panel_backlight|dpu_enc_phys_cmd_pp_tx_done): (.*)', line)
        if match:
            events.append((float(match[1]), match[2], match[3]))
    events.sort()
    tx = None
    waits = []
    for stamp, name, detail in events:
        if name == 'dpu_enc_phys_cmd_pp_tx_done':
            tx = stamp
        elif name == 'dpu_first_frame_backlight':
            waits.append(dict(ret=int(re.search(r'ret=(-?\d+)', detail)[1]), tx_done_seen=tx is not None,
                              tx_to_wait_ms=(stamp-tx)*1000 if tx is not None else None))
    assert waits and all(row['ret'] == 0 and row['tx_done_seen'] and row['tx_to_wait_ms'] >= 0 for row in waits)
    loss_free = all(int(re.search(r'^' + re.escape(name) + r':\s*(\d+)', item, re.M)[1]) == 0
                    for item in stats.values() for name in ['overrun', 'commit overrun', 'dropped events'])
    assert loss_free
    timeline = [line for line in log.splitlines() if any(word in line.lower() for word in
                ['simple-framebuffer', 'simpledrm', 'frame buffer', 'fbcon', 'console: switching',
                 'mdss', 'firmware stop', 'boot ctl', 'inherited ctrl', 'native ctrl', 'sofef03f'])]
report = dict(stage=160, actual_kernel_build=158, same_image_third_boot=True,
              firmware_stop_before_ctl_success=True, one_shot_stop_count=1,
              early_trace_loss_free=loss_free, initial_tx_wait_after_pp_done=waits,
              recorder_start_uptime=float(ready['uptime']), user_reported_startup_speed_improved=True,
              user_reported_white_corruption_between_edk2_and_first_linux_console=True,
              physical_boot_transition_accepted=False, goal_complete=False,
              archive_sha256=hashlib.sha256((out / 'first-evidence-private.tar.gz').read_bytes()).hexdigest())
(ref / 'startup-order-validation.json').write_text(json.dumps(report, indent=2) + '\n')
for name in ['startup-validation.json', 'runtime-validation.json', 'boot-timing-validation.json']:
    (ref / name).write_bytes((out / name).read_bytes())
print(json.dumps(report))
print('\n'.join(timeline))
