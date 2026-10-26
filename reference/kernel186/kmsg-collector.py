"""Bounded /dev/kmsg collection with sequence-gap reporting, private output only."""
from pathlib import Path
import errno
import json
import os
import select
import signal
import sys
import time

os.umask(0o077)
out = Path(sys.argv[1])
out.mkdir(mode=0o700)
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot == Path('/var/lib/samurai/k186-reboot-runtime/boot-id-private.txt').read_bytes()
stop = False
def end(signum, frame):
    global stop
    stop = True
signal.signal(signal.SIGTERM, end)
fd = os.open('/dev/kmsg', os.O_RDONLY | os.O_NONBLOCK)
os.lseek(fd, 0, os.SEEK_END)
count, total, overwritten = 0, 0, 0
gaps = []
last = None
limit = time.monotonic() + 600
(out / 'boot-id-private.txt').write_bytes(boot)
(out / 'ready-private.json').write_text(json.dumps({'pid': os.getpid(), 'ready': True}) + '\n')
try:
    with (out / 'records-private.kmsg').open('xb', buffering=0) as stream:
        while not stop and time.monotonic() < limit:
            if not select.select([fd], [], [], .2)[0]:
                continue
            try:
                record = os.read(fd, 65536)
            except OSError as e:
                if e.errno == errno.EAGAIN:
                    continue
                if e.errno == errno.EPIPE:
                    overwritten += 1
                    continue
                raise
            fields = record.split(b';', 1)[0].split(b',')
            sequence = int(fields[1])
            if last is not None and sequence != last + 1:
                gaps.append({'after': last, 'before': sequence})
            last = sequence
            stream.write(record)
            count += 1
            total += len(record)
            if total > 32 * 1024 * 1024:
                raise RuntimeError('Private kernel log size boundary reached')
finally:
    os.close(fd)
    report = dict(records=count, bytes=total, overwritten_reads=overwritten, sequence_gaps=gaps,
        same_boot=boot == Path('/proc/sys/kernel/random/boot_id').read_bytes(),
        collection_complete_without_gaps=overwritten == 0 and not gaps,
        stopped_by_signal=stop, observation_deadline_seconds=600)
    (out / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
