"""Restore disabled edges before enabled edges, including an aborted application."""
from pathlib import Path
import hashlib,json,subprocess
import host
HERE=Path(__file__).resolve().parent;old=HERE.parent/'kernel299'
s=(old/'pipeline-fixture.c').read_text()
expected=json.loads((old/'inline-smoke-tools-validation.json').read_text())['fixture_source_sha256']
assert hashlib.sha256(s.encode()).hexdigest()==expected
a=s.index(' for(unsigned i=0;i<nl;i++)if(!(links[i].flags&MEDIA_LNK_FL_IMMUTABLE)) {')
b=s.index(' for(unsigned i=0;i<nf;i++) {',a)
s=s[:a]+''' /* An interrupted app may leave a competing input enabled. Remove it first. */
 for(unsigned pass=0;pass<2;pass++)for(unsigned i=0;i<nl;i++)if(!(links[i].flags&MEDIA_LNK_FL_IMMUTABLE)) {
  bool enabled=!!(links[i].flags&MEDIA_LNK_FL_ENABLED);
  if(enabled!=(pass==1))continue;
  struct media_link_desc l=links[i];
  if(call(media,MEDIA_IOC_SETUP_LINK,&l)){perror("fixture restore link");result=1;}
 }
'''+s[b:]
p=HERE/'pipeline-fixture.c';p.write_text(s)
binary=host.PRIVATE/'pipeline-fixture-aarch64-private'
q=subprocess.run(['aarch64-linux-gnu-gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation',
 '-static','-s','-I/mnt/e/edk2-samurai-out/kernel288/host-uapi/include',str(p),'-o',str(binary)],capture_output=True,timeout=120)
(host.PRIVATE/'fixture-compile-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
assert subprocess.run(['qemu-aarch64',str(binary),'/dev/media0','/tmp/never-used'],capture_output=True,timeout=10).returncode==3
out=dict(stage=300,source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
 strict_compile_pass=True,wrong_kernel_guard_pass=True,disabled_links_restored_before_enabled_links=True,
 original299_fixture_preserved=True)
(HERE/'fixture-validation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
