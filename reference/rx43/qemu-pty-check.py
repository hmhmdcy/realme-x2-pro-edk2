"""Audit the actual initramfs BusyBox, with one unsplit ASCII input burst."""
import json
import os
from pathlib import Path
import pty
import select
import subprocess
import termios
import time

base = Path('/mnt/e/edk2-samurai-out/rx43')
master, slave = pty.openpty()
process = subprocess.Popen(
    ['qemu-aarch64', '/home/cy122/x2pro-linux/initramfs/bin/busybox', 'sh', '-i'],
    stdin=slave, stdout=slave, stderr=slave, start_new_session=True)
output = bytearray()

def drain(seconds):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if select.select([master], [], [], .02)[0]:
            output.extend(os.read(master, 4096))

try:
    drain(.5)
    attributes = termios.tcgetattr(slave)
    active = {name: bool(attributes[3] & getattr(termios, name))
              for name in ('ICANON', 'ECHO', 'ISIG')}
    command = b'echo OFFLINE43\n'
    count = os.write(master, command)
    drain(.8)
    assert b'\r\nOFFLINE43\r\n' in output, repr(output)
    result = {'command_hex': command.hex(' '), 'one_write_bytes': count,
              'active_lineedit_termios': active,
              'cursor_query_seen': b'\x1b[6n' in output,
              'cursor_response_sent': False,
              'output': output.decode('ascii', errors='replace')}
    (base / 'qemu-pty.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
finally:
    process.terminate()
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=2)
    os.close(master)
    os.close(slave)
