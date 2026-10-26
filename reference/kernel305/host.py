"""Reuse verified Wi-Fi boot guard; separate S5K3M5 adaptation artifacts."""
from pathlib import Path
import importlib.util,subprocess
spec=importlib.util.spec_from_file_location('transport304',Path(__file__).resolve().parents[1]/'kernel304/host.py')
previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel305');PRIVATE.mkdir(mode=0o700,exist_ok=True)
def raw_ssh(command,**kwargs):
 base=previous.previous.base
 q=subprocess.run([base.SSH,'-T',*base.OPTIONS,'-4','-o','HostKeyAlias=169.254.42.1',
                   'root@169.254.42.1',command],input=kwargs.get('input'),capture_output=True,timeout=kwargs.get('timeout',30))
 if kwargs.get('check',True) and q.returncode:
  (PRIVATE/'usb-last-failure-private.log').write_bytes(q.stdout+q.stderr)
  raise RuntimeError('Original-key USB transport failed; details retained privately')
 return q
def ssh(command,**kwargs):
 q=raw_ssh('cmp -s /proc/sys/kernel/random/boot_id /var/lib/samurai/k305-geometry-r2/boot-id-private.txt',timeout=15)
 assert q.returncode==0
 return raw_ssh(command,**kwargs)
