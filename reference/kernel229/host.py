"""Strict USB transport, current boot228, for daylight camera measurements."""
from pathlib import Path
import importlib.util
import subprocess

PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel229')
PRIVATE.mkdir(exist_ok=True)
spec = importlib.util.spec_from_file_location('usb188', Path(__file__).resolve().parent.parent / 'kernel188/host.py')
transport = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transport)
transport.PRIVATE = PRIVATE


def call(method, *args, **kwargs):
    try:
        return method(*args, **kwargs)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        (PRIVATE / 'transport-last-failure-private.log').write_bytes((error.stdout or b'') + (error.stderr or b''))
        raise RuntimeError('Authenticated229 operation failed; inspect existing case diagnostics') from None


def ssh(command, *, input=None, timeout=60):
    return call(transport.ssh, command, input=input, timeout=timeout)


def upload(source, destination):
    return call(transport.upload, source, destination)
