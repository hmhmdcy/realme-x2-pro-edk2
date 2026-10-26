"""Only the actual reviewed IRQ adoption endpoint, using the original strict key."""
from pathlib import Path
import importlib.util, json, subprocess
HERE = Path(__file__).resolve().parent


def raw_ssh(command, **kwargs):
    spec = importlib.util.spec_from_file_location('icon_irq_transport_identity', HERE / 'launcher.py')
    launcher = importlib.util.module_from_spec(spec); spec.loader.exec_module(launcher)
    launcher.reviewed_identity()
    bound = json.loads(launcher.PINS.read_bytes())
    e = bound['reviewed']['endpoint']; key = bound['transport_inputs']['key_transport']
    if not (e['kind'] == 'usb-ipv6' and e['original_key_verified'] is True
            and e['postboot_USB_IRQ_protection_passed'] is True and e['postboot_Image502_passed'] is True
            and e['peer'] == 'fe80::62:bcff:fe28:a101%29' and e['interface_index'] == 29
            and e['host_key_alias'] == '169.254.42.1'):
        raise ValueError('actual IRQ original-key endpoint required')
    spec = importlib.util.spec_from_file_location('icon_irq_strict_key', key['path'])
    base = importlib.util.module_from_spec(spec); spec.loader.exec_module(base)
    q = subprocess.run([base.SSH, '-C', '-6', '-T', *base.OPTIONS, '-o', 'HostKeyAlias=169.254.42.1',
                        'root@' + e['peer'], command], input=kwargs.get('input'), capture_output=True,
                       timeout=kwargs.get('timeout', 30))
    if kwargs.get('check', True): q.check_returncode()
    return q
