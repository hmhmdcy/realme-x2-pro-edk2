from pathlib import Path
import importlib.util, json, types
spec = importlib.util.spec_from_file_location('transport296', Path(__file__).resolve().parents[1] / 'kernel296/host.py')
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel297')
PRIVATE.mkdir(mode=0o700, exist_ok=True)
base_spec = importlib.util.spec_from_file_location('transport276', Path(__file__).resolve().parents[1] / 'kernel276/host.py')
base = importlib.util.module_from_spec(base_spec)
base_spec.loader.exec_module(base)
fresh = types.FunctionType(base._fresh_raw.__code__, dict(base._fresh_raw.__globals__, PRIVATE=PRIVATE))
def raw_ssh(command, **kwargs):
    if (PRIVATE / 'usb-ipv6-candidates-private.json').exists():
        return fresh(command, **kwargs)
    return previous.raw_ssh(command, **kwargs)
def ssh(command, **kwargs):
    identity = PRIVATE / 'postboot-verified-private.json'
    if not identity.exists():
        return previous.ssh(command, **kwargs)
    expected = json.loads(identity.read_text())['boot_id']
    assert raw_ssh('cat /proc/sys/kernel/random/boot_id', timeout=15).stdout.decode().strip() == expected, 'Boot changed; inspect current state'
    return raw_ssh(command, **kwargs)
