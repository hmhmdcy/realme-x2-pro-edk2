"""Reuse the strict transport; keep AE work and scene data private."""
from pathlib import Path
import importlib.util
import json, subprocess
spec = importlib.util.spec_from_file_location('transport302', Path(__file__).resolve().parents[1] / 'kernel302/host.py')
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel303')
PRIVATE.mkdir(mode=0o700, exist_ok=True)
base_spec = importlib.util.spec_from_file_location('strict303', Path(__file__).resolve().parents[1] / 'kernel190/host.py')
strict = importlib.util.module_from_spec(base_spec)
base_spec.loader.exec_module(strict)
base = strict.transport.parent.transport.base_transport()

def raw_ssh(command, **kwargs):
    endpoint = PRIVATE / 'fresh-working-endpoint-private.json'
    if not endpoint.exists(): return previous.raw_ssh(command, **kwargs)
    selected = json.loads(endpoint.read_text())
    assert selected['kind'] == 'wifi' and selected['proof']['expected_model'] and selected['proof']['same_298_guard']
    q = subprocess.run([base.SSH, '-T', *base.OPTIONS, '-4', '-o', 'HostKeyAlias=169.254.42.1',
                        'root@' + selected['IPAddress'], command], input=kwargs.get('input'), capture_output=True,
                       timeout=kwargs.get('timeout', 30))
    if kwargs.get('check', True) and q.returncode:
        (PRIVATE / 'ssh-last-failure-private.log').write_bytes(q.stdout + q.stderr)
        raise RuntimeError('Strict original-key Wi-Fi SSH failed; inspect private receipt')
    return q

def ssh(command, **kwargs):
    q = raw_ssh('cmp -s /proc/sys/kernel/random/boot_id /var/lib/samurai/k298-work/boot-id-private.txt', timeout=15)
    assert q.returncode == 0
    return raw_ssh(command, **kwargs)
