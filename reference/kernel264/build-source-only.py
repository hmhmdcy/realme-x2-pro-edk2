"""Test whether proxy and real source must avoid duplicate pool reconfiguration."""
from pathlib import Path
import difflib,hashlib,json,shutil,subprocess
R=Path(__file__).parent;P=Path('/mnt/e/edk2-samurai-out/kernel264');P.mkdir(exist_ok=True)
SDK=Path('/home/cy122/x2pro-linux/libcamera214-root');W=SDK/'work/pipewire263-broadcast';p=W/'pipewire-1.6.9/src/pipewire/impl-port.c'
# Reconstruct the previous public patch to verify the actual working source.
fixture=P/'verify-previous-source';assert not fixture.exists();target=fixture/'src/pipewire/impl-port.c';target.parent.mkdir(parents=True)
original=(SDK/'work/pipewire262/pipewire-1.6.9/src/pipewire/impl-port.c').read_text();target.write_text(original)
q=subprocess.run(['patch','--silent','-p1','-d',str(fixture)],input=(R.parent/'kernel263/core-broadcast-reconfigure-candidate.patch').read_bytes(),capture_output=True);assert q.returncode==0
s=p.read_text();assert s==target.read_text(),'Unexpected SDK source; inspect before replacing'
(P/'core-ff2954-source-before-private.c').write_text(s)
needle='''port->direction == PW_DIRECTION_OUTPUT && port->node &&
			SPA_CONTAINER_OF(port, struct impl, this)->reliable_broadcast'''
assert s.count(needle)==1
s=s.replace(needle,'''port->direction == PW_DIRECTION_OUTPUT && port->node && !port->node->remote &&
			SPA_CONTAINER_OF(port, struct impl, this)->reliable_broadcast''')
s=s.replace('''pw_log_info("%p: rebuild camera pool after consumer removal", port);''','''pw_log_info("%p: rebuild camera pool after consumer removal remote:%d exported:%d",
			port, node->remote, node->exported);''')
p.write_text(s)
(R/'core-source-only-reconfigure-candidate.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),s.splitlines(True),fromfile='a/src/pipewire/impl-port.c',tofile='b/src/pipewire/impl-port.c')))
q=subprocess.run(['chroot',str(SDK),'ninja','-C','/work/pipewire263-broadcast/build','-j2','src/pipewire/libpipewire-0.3.so.0.1609.0'],capture_output=True)
(P/'source-only-build-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,(q.stdout+q.stderr).decode(errors='replace')[-2500:]
shutil.copyfile(W/'build/src/pipewire/libpipewire-0.3.so.0.1609.0',P/'libpipewire-source-only-candidate.so')
spa=P.parent/'kernel263/libspa-libcamera-broadcast-candidate.so';assert hashlib.sha256(spa.read_bytes()).hexdigest()=='bdd70ab54a9705dbd50329716988f7d4e8908b4759f5f7cb75f4b921c32908c5'
shutil.copyfile(spa,P/spa.name)
report=dict(stage=264,compiled=True,source_sha256=hashlib.sha256(s.encode()).hexdigest(),core_sha256=hashlib.sha256((P/'libpipewire-source-only-candidate.so').read_bytes()).hexdigest(),spa_sha256=hashlib.sha256(spa.read_bytes()).hexdigest(),busy_counters_never_reset=True,no_system_deployment=True)
(R/'source-only-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
