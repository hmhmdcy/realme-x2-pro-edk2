"""Strict original SSH keys and scoped USB endpoint; current boot236 only."""
from pathlib import Path
import importlib.util
import subprocess

PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel237')
spec = importlib.util.spec_from_file_location('usb237', Path(__file__).resolve().parent.parent / 'kernel188/host.py')
transport = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transport)
transport.PRIVATE = PRIVATE


def call(function, *args, **kwargs):
    try:
        return function(*args, **kwargs)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        (PRIVATE / 'transport-last-failure-private.log').write_bytes((error.stdout or b'') + (error.stderr or b''))
        raise RuntimeError('Authenticated237 operation failed; inspect private receipt before retry') from None


def ssh(command, *, input=None, timeout=60):
    return call(transport.ssh, command, input=input, timeout=timeout)


def upload(source, destination):
    return call(transport.upload, source, destination)


def download(source, destination):
    return call(transport.download, source, destination)
