"""Reuse the current strict-key USB transport; never publish private endpoints."""
from pathlib import Path
import importlib.util

PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel262')
PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
spec = importlib.util.spec_from_file_location('current_transport', PRIVATE.parent / 'kernel260/host.py')
transport = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transport)


def ssh(command, **kwargs):
    transport.guard()
    return transport.ssh(command, **kwargs)
