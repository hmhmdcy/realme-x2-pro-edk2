"""Read bounded firmware and console messages around the trace gap."""
from pathlib import Path
import json
import re
import tarfile

out = Path('/mnt/e/edk2-samurai-out/kernel142')
with tarfile.open(out / 'reboot140-startup-private.tar.gz') as archive:
    data = {name: archive.extractfile('./'+name).read().decode(errors='replace')
        for name in ['dmesg-final-private.txt', 'default-display-early-private.txt']}
for line in data['dmesg-final-private.txt'].splitlines():
    match = re.match(r'\[\s*(\d+\.\d+)\]', line)
    if match and 55.8 <= float(match[1]) <= 57.2:
        print(re.sub(r'0x[0-9a-fA-F]+|\b[0-9a-fA-F]{12,16}\b', '[address]', line))
trace = data['default-display-early-private.txt']
events = []
pattern = re.compile(r'\[(\d+)\].*?\s(\d+\.\d+):\s+([A-Za-z0-9_]+):\s*(.*)$')
for line in trace.splitlines():
    match = pattern.search(line)
    if match:
        events.append(dict(cpu=int(match[1]), seconds=float(match[2]), name=match[3], body=match[4]))
for index, event in enumerate(events):
    if event['name'] == 'dpu_enc_frame_done_timeout':
        print('DEFAULT EARLY TIMEOUT', event['seconds'])
        for row in events[max(0,index-12):index+8]:
            body = re.sub(r'0x[0-9a-fA-F]+|\b[0-9a-fA-F]{12,16}\b', '[address]', row['body'])
            print(row['cpu'], row['seconds'], row['name'], body)
root = Path('/home/cy122/pmos-samurai-kernel136/kernel')
for name, expression in [('drivers/tty/serial/qcom_geni_serial.c', r'console_write|irqsave|write_buf|poll_put_char'),
    ('drivers/tty/serial/eud_earlycon.c', r'console|write|irq|putc|while|timeout'),
    ('.config', r'CONFIG_(SERIAL|PRINTK|PREEMPT|CONSOLE)')]:
    path = root/name
    if not path.exists():
        continue
    print(name)
    for number, line in enumerate(path.read_text().splitlines(),1):
        if re.search(expression, line):
            print(f'{number}: {line}')
