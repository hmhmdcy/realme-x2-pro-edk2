"""Use the verified boot270 guard until the new boot is independently adopted."""
from pathlib import Path
import importlib.util,json,subprocess
spec=importlib.util.spec_from_file_location('camera270_transport',Path(__file__).resolve().parents[1]/'kernel270/host.py')
previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel273');PRIVATE.mkdir(mode=0o700,exist_ok=True)

def raw_ssh(command,**kwargs):
 peer=PRIVATE/'usb-ipv6-candidates-private.json'
 if not peer.exists():return previous.raw_ssh(command,**kwargs)
 address=json.loads(peer.read_text(encoding='utf-8-sig'))['IPAddress']
 base=previous.previous.transport.transport.previous
 q=subprocess.run([base.base['ssh'],'-T','-6',*base.OPTIONS,'root@'+address,command],
  input=kwargs.get('input'),capture_output=True,timeout=kwargs.get('timeout',30))
 if kwargs.get('check',True) and q.returncode:
  (PRIVATE/'ssh-last-failure-private.log').write_bytes(q.stdout+q.stderr)
  raise RuntimeError('Strict original-key USB SSH failed; inspect private receipt')
 return q

def ssh(command,**kwargs):
 identity=PRIVATE/'postboot-verified-private.json'
 if not identity.exists():identity=PRIVATE.parent/'kernel270/postboot-verified-private.json'
 expected=json.loads(identity.read_text())['boot_id']
 q=raw_ssh('cat /proc/sys/kernel/random/boot_id',timeout=15)
 assert q.stdout.decode().strip()==expected,'Boot changed; inspect actual boot/crash evidence before further operations'
 return raw_ssh(command,**kwargs)
