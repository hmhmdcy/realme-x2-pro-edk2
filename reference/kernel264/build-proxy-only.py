"""Keep camera renegotiation at the proxy that owns the surviving links."""
from pathlib import Path
import difflib,hashlib,json,shutil,subprocess
R=Path(__file__).parent;P=Path('/mnt/e/edk2-samurai-out/kernel264');SDK=Path('/home/cy122/x2pro-linux/libcamera214-root');W=SDK/'work/pipewire263-broadcast';p=W/'pipewire-1.6.9/src/pipewire/impl-port.c'
s=p.read_text();assert hashlib.sha256(s.encode()).hexdigest()==json.loads((R/'source-only-build-validation.json').read_text())['source_sha256']
(P/'core-source-only-before-private.c').write_text(s)
needle='port->node && !port->node->remote &&';assert s.count(needle)==1;s=s.replace(needle,'port->node && port->node->remote &&')
p.write_text(s);original=(SDK/'work/pipewire262/pipewire-1.6.9/src/pipewire/impl-port.c').read_text()
(R/'core-proxy-only-reconfigure-candidate.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),s.splitlines(True),fromfile='a/src/pipewire/impl-port.c',tofile='b/src/pipewire/impl-port.c')))
q=subprocess.run(['chroot',str(SDK),'ninja','-C','/work/pipewire263-broadcast/build','-j2','src/pipewire/libpipewire-0.3.so.0.1609.0'],capture_output=True)
(P/'proxy-only-build-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,(q.stdout+q.stderr).decode(errors='replace')[-2500:]
shutil.copyfile(W/'build/src/pipewire/libpipewire-0.3.so.0.1609.0',P/'libpipewire-proxy-only-candidate.so')
report=dict(stage=264,compiled=True,source_sha256=hashlib.sha256(s.encode()).hexdigest(),core_sha256=hashlib.sha256((P/'libpipewire-proxy-only-candidate.so').read_bytes()).hexdigest(),spa_sha256=hashlib.sha256((P/'libspa-libcamera-broadcast-candidate.so').read_bytes()).hexdigest(),busy_counters_never_reset=True,no_system_deployment=True)
(R/'proxy-only-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
