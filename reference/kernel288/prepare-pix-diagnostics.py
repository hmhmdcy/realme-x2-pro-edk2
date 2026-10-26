"""Hold streaming through a bounded handshake so MMIO is read with its clocks owned."""
from pathlib import Path
import hashlib,json,subprocess

ROOT=Path(__file__).resolve().parent;PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel288')
s=(ROOT/'samurai-pix-tpg-capture.c').read_text()
old=' if(call(video,VIDIOC_STREAMON,&type))goto cleanup;streaming=true;'
assert s.count(old)==1
s=s.replace(old,old+'''
 puts("STREAMON_OK");fflush(stdout);
 if(getenv("SAMURAI_PIX_SNAPSHOT")){
  struct pollfd gate={.fd=STDIN_FILENO,.events=POLLIN};
  if(poll(&gate,1,10000)<=0){errno=ETIMEDOUT;goto cleanup;}
  char token;if(read(STDIN_FILENO,&token,1)!=1){errno=EIO;goto cleanup;}
 }
''')
p=ROOT/'samurai-pix-tpg-diagnostic.c';assert not p.exists();p.write_text(s)
binary=PRIVATE/'pix-diagnostic-aarch64-private'
q=subprocess.run(['aarch64-linux-gnu-gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-static','-s','-I'+str(PRIVATE/'host-uapi/include'),str(p),'-o',str(binary)],capture_output=True)
(PRIVATE/'pix-diagnostic-compile-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
q=subprocess.run(['qemu-aarch64',str(binary),'--self-test'],capture_output=True,timeout=10);assert q.returncode==0
report=dict(stage=288,binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),binary_bytes=binary.stat().st_size,
            source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),qemu_self_test_pass=True,
            stream_held_until_parent_handshake=True,maximum_handshake_ms=10000,not_run_on_phone=True)
(ROOT/'pix-diagnostic-tool-validation.json').write_text(json.dumps(report,indent=2)+'\n')
launch=(ROOT/'launch-pix-tpg.py').read_text()
for old,new in [('tpg-tool-validation.json','pix-diagnostic-tool-validation.json'),('pix-tpg-aarch64-private','pix-diagnostic-aarch64-private'),('pix-tpg-capture','pix-tpg-diagnostic'),('native-pix-tpg.py','native-pix-diagnostic.py'),('k288-tpg-r1','k288-tpg-r2'),('tpg-worker-private.log','pix-diagnostic-worker-private.log'),('tpg-launch-private.json','pix-diagnostic-launch-private.json')]:launch=launch.replace(old,new)
(ROOT/'launch-pix-diagnostic.py').write_text(launch)
poll=(ROOT/'poll-pix-tpg.py').read_text().replace('tpg-launch-private.json','pix-diagnostic-launch-private.json').replace('k288-tpg-r1','k288-tpg-r2').replace('tpg-poll-private.json','pix-diagnostic-poll-private.json').replace('tpg-r1-validation.json','tpg-r2-validation.json')
(ROOT/'poll-pix-diagnostic.py').write_text(poll)
print(json.dumps(report,indent=2))
