"""Build an unchanged RDI-path positive control for the current kernel and graph."""
from pathlib import Path
import hashlib,json,subprocess

ROOT=Path(__file__).resolve().parent;PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel288')
s=(ROOT.parent/'kernel126/samurai-tpg-capture.c').read_text().replace('7.3.0-rc6-rmx1931-samurai-k126+','7.3.0-rc6-rmx1931-samurai-k279candidate+')
s=s.replace('if(uname(&identity)||strcmp(identity.release,"7.3.0-rc6-rmx1931-samurai-k279candidate+"))','if(uname(&identity)||strcmp(identity.release,"7.3.0-rc6-rmx1931-samurai-k279candidate+")||strncmp(identity.version,"#288 ",5))')
p=ROOT/'samurai-rdi-tpg-control.c';assert not p.exists();p.write_text(s)
binary=PRIVATE/'rdi-tpg-aarch64-private'
q=subprocess.run(['aarch64-linux-gnu-gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-static','-s','-I'+str(PRIVATE/'host-uapi/include'),str(p),'-o',str(binary)],capture_output=True)
(PRIVATE/'rdi-tpg-compile-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
q=subprocess.run(['qemu-aarch64',str(binary),'--self-test'],capture_output=True,timeout=10);assert q.returncode==0
report=dict(stage=288,binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),binary_bytes=binary.stat().st_size,
            source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),qemu_self_test_pass=True,
            unchanged_rdi_capture_algorithm=True,format='SGRBG10P',frames=3,not_run_on_phone=True)
(ROOT/'rdi-control-tool-validation.json').write_text(json.dumps(report,indent=2)+'\n')
worker=(ROOT/'native-pix-tpg.py').read_text().replace('k288-tpg-r1','k288-rdi-control-r1').replace('pix-tpg-capture','rdi-tpg-control').replace('first-nv12-private.raw','first-rdi-private.raw')
start=worker.index('  b=frame.read_bytes();assert len(b)==320*240*3//2')
end=worker.index('\n report=dict(',start)
worker=worker[:start]+'''  b=frame.read_bytes();assert len(b)==400*240
  image=dict(bytes=len(b),byte_min=min(b),byte_max=max(b),different_byte_values=len(set(b)))
'''+worker[end:]
(ROOT/'native-rdi-control.py').write_text(worker)
launch=(ROOT/'launch-pix-tpg.py').read_text()
for old,new in [('tpg-tool-validation.json','rdi-control-tool-validation.json'),('pix-tpg-aarch64-private','rdi-tpg-aarch64-private'),('pix-tpg-capture','rdi-tpg-control'),('native-pix-tpg.py','native-rdi-control.py'),('k288-tpg-r1','k288-rdi-control-r1'),('tpg-worker-private.log','rdi-control-worker-private.log'),('tpg-launch-private.json','rdi-control-launch-private.json')]:
 launch=launch.replace(old,new)
(ROOT/'launch-rdi-control.py').write_text(launch)
poll=(ROOT/'poll-pix-tpg.py').read_text().replace('tpg-launch-private.json','rdi-control-launch-private.json').replace('k288-tpg-r1','k288-rdi-control-r1').replace('tpg-poll-private.json','rdi-control-poll-private.json').replace('tpg-r1-validation.json','rdi-control-validation.json')
(ROOT/'poll-rdi-control.py').write_text(poll)
print(json.dumps(report,indent=2))
