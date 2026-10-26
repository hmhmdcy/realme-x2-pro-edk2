"""Resume after Meson's disabled-SPA configuration bug; retain failed log."""
from pathlib import Path
import difflib,hashlib,json,shutil,subprocess
R=Path(__file__).parent;P=Path('/mnt/e/edk2-samurai-out/kernel263');SDK=Path('/home/cy122/x2pro-linux/libcamera214-root');W=SDK/'work/pipewire263-broadcast';base=SDK/'work/pipewire262/pipewire-1.6.9'
assert (W/'pipewire-1.6.9/src/pipewire/impl-port.c').exists()
def inside(args,log):
 q=subprocess.run(['chroot',str(SDK),*args],capture_output=True);(P/log).write_bytes(q.stdout+q.stderr)
 if q.returncode:print((q.stdout+q.stderr).decode(errors='replace')[-5000:]);raise RuntimeError(log)
 return q
s=(R/'build-broadcast-candidate.py').read_text();s=s[s.index("prefix='/work/pipewire263-broadcast'"):]
s=s.replace('-Dspa-plugins=disabled','-Dspa-plugins=enabled').replace('broadcast-core-configure-private.log','broadcast-core-configure-r2-private.log')
exec(compile(s,str(__file__)+'-continuation','exec'))
