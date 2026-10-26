"""Strict-key transport bound to the independently inspected current boot."""
from pathlib import Path
import importlib.util,json,subprocess
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel270')
spec=importlib.util.spec_from_file_location('transport269',Path(__file__).resolve().parents[1]/'kernel269/host.py')
previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
def raw_ssh(command,**kwargs):
 peer=PRIVATE/'usb-ipv6-candidates-private.json'
 if not peer.exists():return previous.transport.raw_ssh(command,**kwargs)
 address=json.loads(peer.read_text(encoding='utf-8-sig'))['IPAddress']
 base=previous.transport.transport.previous
 q=subprocess.run([base.base['ssh'],'-T','-6',*base.OPTIONS,'root@'+address,command],input=kwargs.get('input'),capture_output=True,timeout=kwargs.get('timeout',30))
 if kwargs.get('check',True) and q.returncode:
  (PRIVATE/'ssh-last-failure-private.log').write_bytes(q.stdout+q.stderr)
  raise RuntimeError('Strict original-key USB SSH failed; inspect the private receipt')
 return q
def ssh(command,**kwargs):
 identity=PRIVATE/'postboot-verified-private.json'
 if not identity.exists():identity=PRIVATE/'current-inspection-private.json'
 expected=json.loads(identity.read_text())['boot_id']
 observed=raw_ssh('cat /proc/sys/kernel/random/boot_id',timeout=15)
 assert observed.stdout.decode().strip()==expected,'Boot changed; preserve and inspect new crash evidence before proceeding'
 return raw_ssh(command,**kwargs)
