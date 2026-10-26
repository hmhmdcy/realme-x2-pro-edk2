"""Strict USB transport; stage188 private evidence stays outside the repository."""
from pathlib import Path
import importlib.util
import json
import re
import subprocess

spec = importlib.util.spec_from_file_location('transport', Path(__file__).resolve().parent.parent / 'kernel186/host.py')
transport = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transport)
ssh, upload, download = transport.ssh, transport.upload, transport.download
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel188')
PRIVATE.mkdir(exist_ok=True)

def endpoint():
    candidate = PRIVATE / 'usb-ipv6-candidates-private.json'
    if not candidate.exists():
        return [], '169.254.42.1'
    record = json.loads(candidate.read_text(encoding='utf-8-sig'))
    address = record['IPAddress']
    if not re.fullmatch(r'fe80:[0-9a-fA-F:]+%[0-9]+', address):
        raise ValueError('Expected scoped USB link-local address')
    return ['-6', '-o', 'HostKeyAlias=169.254.42.1'], address

def base_transport():
    # Follow the existing import chain to the implementation, preserving strict keys.
    base = transport
    while hasattr(base, 'transport'):
        base = base.transport
    return base

def ssh(command, *, input=None, timeout=60):
    base = base_transport()
    extra, address = endpoint()
    return subprocess.run([base.SSH, '-T', *base.OPTIONS, *extra, 'root@' + address, command],
        input=input, capture_output=True, timeout=timeout, check=True)

def upload(path, destination):
    base = base_transport()
    path = Path(path).resolve()
    if not str(path).startswith('/mnt/e/'):
        raise ValueError('Upload source must be on E drive')
    extra, address = endpoint()
    remote = '[' + address + ']' if ':' in address else address
    windows = 'E:/' + str(path)[len('/mnt/e/'):]
    return subprocess.run([base.SCP, '-O', *base.OPTIONS, *extra, windows, 'root@' + remote + ':' + destination],
        capture_output=True, timeout=60, check=True)

def download(source, destination):
    base = base_transport()
    destination = Path(destination).resolve()
    if not str(destination).startswith('/mnt/e/edk2-samurai-out/'):
        raise ValueError('Evidence must stay in private output tree')
    extra, address = endpoint()
    remote = '[' + address + ']' if ':' in address else address
    windows = 'E:/' + str(destination)[len('/mnt/e/'):]
    return subprocess.run([base.SCP, '-O', *base.OPTIONS, *extra, 'root@' + remote + ':' + source, windows],
        capture_output=True, timeout=120, check=True)
