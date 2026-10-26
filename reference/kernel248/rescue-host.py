"""Strict SSH to the separately pinned builtin RAM recovery environment."""
from pathlib import Path
import importlib.util,subprocess
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel248');spec=importlib.util.spec_from_file_location('current',R.parent/'kernel247/host.py');current=importlib.util.module_from_spec(spec);spec.loader.exec_module(current);base=current.transport.transport.base_transport()
def ssh(command,*,input=None,timeout=30):
 extra=['-o','UserKnownHostsFile=E:/edk2-samurai-out/kernel248/rescue-known-hosts-private','-o','GlobalKnownHostsFile=NUL','-o','StrictHostKeyChecking=yes','-o','HostKeyAlias=169.254.42.1']
 try:return subprocess.run([base.SSH,'-T','-4',*extra,*base.OPTIONS,'root@169.254.42.1',command],input=input,capture_output=True,check=True,timeout=timeout)
 except (subprocess.CalledProcessError,subprocess.TimeoutExpired) as e:
  (P/'rescue-transport-last-failure-private.log').write_bytes((e.stdout or b'')+(e.stderr or b''));raise RuntimeError('RAM recovery SSH failed; inspect private receipt, never accept a new key') from None
