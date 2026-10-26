"""Current guarded USB transport, with separate private stage267 evidence."""
from pathlib import Path
import importlib.util
import json
import subprocess

PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel267')
PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
spec = importlib.util.spec_from_file_location('current_transport', PRIVATE.parent/'kernel260/host.py')
transport = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transport)

def raw_ssh(command, **kwargs):
    peer=PRIVATE/'usb-ipv6-candidates-private.json'
    if not peer.exists():return transport.ssh(command, **kwargs)
    address=json.loads(peer.read_text(encoding='utf-8-sig'))['IPAddress']
    base=transport.previous
    q=subprocess.run([base.base['ssh'],'-T','-6',*base.OPTIONS,'root@'+address,command],
      input=kwargs.get('input'),capture_output=True,timeout=kwargs.get('timeout',30))
    if kwargs.get('check',True) and q.returncode:
        (PRIVATE/'ssh-last-failure-private.log').write_bytes(q.stdout+q.stderr)
        raise RuntimeError('Strict original-key USB SSH failed; inspect private receipt')
    return q

def ssh(command, **kwargs):
    identity = PRIVATE/'postboot-verified-private.json'
    if identity.exists():
        q = raw_ssh('cat /proc/sys/kernel/random/boot_id', timeout=15)
        assert q.stdout.strip().decode() == json.loads(identity.read_text())['boot_id']
    else:
        q=raw_ssh('cat /proc/sys/kernel/random/boot_id', timeout=15)
        assert q.stdout.strip()==(PRIVATE.parent/'kernel260/linux-boot-id-private.txt').read_bytes().strip()
    return raw_ssh(command, **kwargs)
