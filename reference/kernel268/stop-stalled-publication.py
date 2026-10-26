"""Stop only the observed stalled local Git push; never act on the phone."""
from pathlib import Path
import json,os,signal,subprocess,time
P=Path('/mnt/e/edk2-samurai-out/kernel268');receipt=P/'stalled-push-stop-private.json';assert not receipt.exists()
parent=Path('/proc/363453');assert b'push-kernel-sources.py' in (parent/'cmdline').read_bytes()
chain=[(363486,363453,'git'),(363487,363486,'git'),(363488,363487,'git-remote-http')]
for pid,ppid,comm in chain:
 p=Path('/proc',str(pid));assert (p/'comm').read_text().strip()==comm
 assert int((p/'stat').read_text().rsplit(')',1)[1].split()[1])==ppid
for pid,_,_ in reversed(chain):
 try:os.kill(pid,signal.SIGTERM)
 except ProcessLookupError:pass
receipt.write_text(json.dumps(dict(stopped_only_observed_local_push=True,observed_pids=[p for p,_,_ in chain]))+'\n')
print('Stopped the observed stalled local publication process; remote state must be rechecked before retry.')
