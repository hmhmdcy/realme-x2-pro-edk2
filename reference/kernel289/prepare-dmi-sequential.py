"""Retain r1; compare sequential auto-increment reads after all queued frames finish."""
from pathlib import Path
import hashlib,json,subprocess
import host

ROOT=Path(__file__).resolve().parent
h=(ROOT/'dmi-readback.h').read_text()
h=h.replace('for(unsigned i=0;i<64;i++){\n   mmio_write(base,0xc28,i);uint32_t value=mmio_read(base,0xc30);',
 '''mmio_write(base,0xc28,0);
  for(unsigned i=0;i<64;i++){
   if(!auto_inc)mmio_write(base,0xc28,i);
   uint32_t value=mmio_read(base,0xc30);''')
header=ROOT/'dmi-sequential.h';assert not header.exists();header.write_text(h)
s=(ROOT/'samurai-dmi-readback.c').read_text().replace('"dmi-readback.h"','"dmi-sequential.h"')
assert s.count(' if(gamma_readback())goto cleanup;')==1
s=s.replace(' if(gamma_readback())goto cleanup;','')
s=s.replace(' result=0;\ncleanup:',' if(gamma_readback())goto cleanup;\n result=0;\ncleanup:')
source=ROOT/'samurai-dmi-sequential.c';assert not source.exists();source.write_text(s)
binary=host.PRIVATE/'dmi-sequential-aarch64-private'
q=subprocess.run(['aarch64-linux-gnu-gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-static','-s','-I/mnt/e/edk2-samurai-out/kernel288/host-uapi/include',str(source),'-o',str(binary)],capture_output=True)
(host.PRIVATE/'dmi-sequential-compile-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
q=subprocess.run(['qemu-aarch64',str(binary),'--self-test'],capture_output=True,timeout=10);assert q.returncode==0
report=dict(stage=289,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),header_sha256=hashlib.sha256(header.read_bytes()).hexdigest(),
 binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),bytes=binary.stat().st_size,qemu_content_self_test=True,
 no_lut_data_writes=True,readback_after_three_queued_frames=True,auto_increment_reads_are_sequential=True,not_run_on_phone=True)
(ROOT/'dmi-sequential-tool-validation.json').write_text(json.dumps(report,indent=2)+'\n')
for src,dst in [('native-dmi-readback.py','native-dmi-sequential.py'),('launch-dmi-readback.py','launch-dmi-sequential.py'),('poll-dmi-readback.py','poll-dmi-sequential.py')]:
 s=(ROOT/src).read_text()
 for a,b in [('k289-dmi-r1','k289-dmi-r2'),('dmi-tool-validation.json','dmi-sequential-tool-validation.json'),('dmi-readback-aarch64-private','dmi-sequential-aarch64-private'),('native-dmi-readback.py','native-dmi-sequential.py'),('dmi-readback','dmi-sequential'),('dmi-launch-private','dmi-sequential-launch-private'),('dmi-worker-private','dmi-sequential-worker-private'),('dmi-poll-private','dmi-sequential-poll-private'),('dmi-capture-validation.json','dmi-sequential-capture-validation.json'),('gamma-lut-readback-validation.json','gamma-lut-sequential-validation.json')]:s=s.replace(a,b)
 if dst.startswith('launch-'):s=s.replace("p.mkdir(mode=0o700)","p.mkdir(mode=0o700,exist_ok=True)")
 (ROOT/dst).write_text(s)
print(json.dumps(report,indent=2))
