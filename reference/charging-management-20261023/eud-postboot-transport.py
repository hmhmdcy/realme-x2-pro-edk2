"""Original pinned-key transport to the actually adopted EUD-off new boot."""
from pathlib import Path
import importlib.util, json, subprocess

REF = Path(__file__).resolve().parent
ENDPOINT = Path('/mnt/e/edk2-samurai-out/charging-management-20261023/eud-boot-activation/eud-boot-r2-live-001/new-endpoint-private.json')
spec = importlib.util.spec_from_file_location('original_key', REF.parent/'kernel184/host.py')
base = importlib.util.module_from_spec(spec); spec.loader.exec_module(base)

def raw_ssh(command, **kwargs):
    e=json.loads(ENDPOINT.read_bytes())
    assert e['kind']=='usb-ipv6' and e['original_key_verified'] and e['postboot_R3_passed']
    assert e['peer']=='fe80::62:bcff:fe28:a101%29' and e['interface_index']==29
    assert e['host_key_alias']=='169.254.42.1'
    q=subprocess.run([base.SSH,'-6','-T',*base.OPTIONS,'-o','HostKeyAlias=169.254.42.1',
                      'root@'+e['peer'],command],input=kwargs.get('input'),capture_output=True,
                     timeout=kwargs.get('timeout',30))
    if kwargs.get('check',True): q.check_returncode()
    return q
