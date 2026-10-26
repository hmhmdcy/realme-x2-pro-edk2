#!/usr/bin/env python3
"""Print only display metadata; keep the original logs private."""
import json
import re
import tarfile
from pathlib import Path

root = Path('/mnt/e/edk2-samurai-out/kernel108')
for name in ('display-live-first.tar', 'display-live-detail.tar'):
    path = root / name
    if not path.exists():
        continue
    with tarfile.open(path) as tar:
        entries = {}
        for member in tar.getmembers():
            if member.isfile():
                entries[Path(member.name).name] = tar.extractfile(member).read().decode(errors='replace')
    print(name)
    for key, value in entries.items():
        if 'dmesg' in key:
            lines = [line for line in value.splitlines() if re.search(r'dsi_err_worker|frame.done|underflow|samsung|samurai.panel|panel.*error', line, re.I)]
            print(json.dumps({'file': key, 'matched': len(lines), 'first': lines[:8], 'last': lines[-12:]}, ensure_ascii=False))
        elif any(s in key for s in ('brightness', 'bl_power', 'max_brightness', '-modes', '-status', '-enabled', 'encoder', 'drm-state', 'dri_1_state', 'uptime')):
            print(key, value[:8000])
        elif key == 'drm-debug-files.txt':
            print(key, value)

source = Path('/home/cy122/x2pro-linux/linux/arch/arm64/boot/dts/qcom/sm8150-samurai.dts').read_text()
for index, line in enumerate(source.splitlines(), 1):
    if re.search(r'panel|backlight|dsi|display', line, re.I):
        print(f'DTS {index}: {line}')
for directory in ('drivers/gpu/drm/panel', 'drivers/gpu/drm/msm/dsi'):
    for file in (Path('/home/cy122/x2pro-linux/linux') / directory).glob('*.c'):
        if 'samurai' in file.name:
            print('PANEL_SOURCE', file)
