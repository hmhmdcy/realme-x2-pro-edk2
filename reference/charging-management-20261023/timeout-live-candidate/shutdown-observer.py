"""Recognize the actual root OpenRC shutdown process without changing policy."""
from pathlib import Path
import stat


def pending_openrc_shutdown(proc=Path('/proc'), executable=Path('/sbin/openrc')):
    expected = executable.stat()
    if not stat.S_ISREG(expected.st_mode) or expected.st_uid != 0 or expected.st_mode & 0o022:
        raise RuntimeError('OpenRC executable identity is not trusted')
    for process in proc.glob('[0-9]*'):
        try:
            words = (process / 'cmdline').read_bytes().split(b'\0')
            if len(words) != 3 or words[1] != b'shutdown' or words[2] != b'':
                continue
            if words[0].rsplit(b'/', 1)[-1] != b'openrc':
                continue
            before = (process / 'stat').read_text().rsplit(')', 1)[1].split()
            if before[0] in ['Z', 'X']:
                continue
            actual = (process / 'exe').stat()
            if (actual.st_dev, actual.st_ino) != (expected.st_dev, expected.st_ino):
                continue
            uid = next(line.split()[1:] for line in (process / 'status').read_text().splitlines()
                       if line.startswith('Uid:'))
            if uid != ['0', '0', '0', '0']:
                continue
            after = (process / 'stat').read_text().rsplit(')', 1)[1].split()
            if before[19] != after[19] or after[0] in ['Z', 'X']:
                continue
            return dict(action='openrc_shutdown', pid=int(process.name), startticks=int(after[19]))
        except (FileNotFoundError, ProcessLookupError):
            continue
    return None
