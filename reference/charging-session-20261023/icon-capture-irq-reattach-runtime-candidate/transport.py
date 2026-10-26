"""Fixed original-key SSH callback prepared before the collector's timed call."""
from pathlib import Path
import hashlib, importlib.util, subprocess, sys
sys.dont_write_bytecode = True
if sys.flags.optimize: raise RuntimeError('non-optimized Python required')
HERE = Path(__file__).resolve().parent
KEY = '7f49a922e0babf167c77ad6e9bd7edf63e437418d5134e3d081fb8a0082a4f4c'


def prevalidated(e, entries):
    """Caller completed source/evidence review; this callback does no local review."""
    key = entries['key_transport']
    if not (e['kind'] == 'usb-ipv6' and e['original_key_verified'] is True
            and e['postboot_USB_IRQ_protection_passed'] is True and e['postboot_Image502_passed'] is True
            and e['peer'] == 'fe80::62:bcff:fe28:a101%29' and e['interface_index'] == 29
            and e['host_key_alias'] == '169.254.42.1'):
        raise ValueError('actual IRQ original-key endpoint required')
    if key['sha256'] != KEY or hashlib.sha256(Path(key['path']).read_bytes()).hexdigest() != KEY:
        raise ValueError('original strict key source changed')
    spec = importlib.util.spec_from_file_location('icon_irq_strict_key', key['path'])
    base = importlib.util.module_from_spec(spec); spec.loader.exec_module(base)
    argv = [base.SSH, '-C', '-6', '-T', *base.OPTIONS, '-o', 'HostKeyAlias=169.254.42.1', 'root@' + e['peer']]
    def observe(command, **kwargs):
        q = subprocess.run([*argv, command], input=kwargs.get('input'), capture_output=True,
                           timeout=kwargs.get('timeout', 30))
        if kwargs.get('check', True): q.check_returncode()
        return q
    return observe


def raw_ssh(command, **kwargs):
    spec = importlib.util.spec_from_file_location('icon_runtime_transport_identity', HERE / 'launcher.py')
    launcher = importlib.util.module_from_spec(spec); spec.loader.exec_module(launcher)
    actual, entries = launcher.identity()
    return prevalidated(actual['endpoint'], entries)(command, **kwargs)
