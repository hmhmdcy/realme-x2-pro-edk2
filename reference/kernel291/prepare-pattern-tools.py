"""Add sensor-internal color bars to the same physical CSI and PIX/RDI probes."""
from pathlib import Path
import hashlib,json,subprocess
import host
ROOT=Path(__file__).resolve().parent
reports={}
for name in ['raw','pix']:
 s=(ROOT/f'samurai-physical-{name}.c').read_text()
 old='if(argc!=3||strcmp(argv[1],"--capture"))';new='if(argc!=3||strcmp(argv[1],"--pattern"))'
 assert old in s;s=s.replace(old,new)
 old='if(call(csid,VIDIOC_S_CTRL,&off)||call(sensor,VIDIOC_S_CTRL,&off))goto cleanup;'
 assert old in s;s=s.replace(old,'if(call(csid,VIDIOC_S_CTRL,&off))goto cleanup;off.value=2;if(call(sensor,VIDIOC_S_CTRL,&off))goto cleanup;')
 s=s.replace('sensor_tpg=0 csid_tpg=0','sensor_tpg=2 csid_tpg=0')
 if name=='raw':
  needle='  for(size_t n=0;n<sizes[buffer.index];n++)data[n]=prefill(fills[buffer.index],n);'
  assert needle in s
  s=s.replace(needle,r'''
  if(frame==5||frame==11||frame==17)for(unsigned bar=0;bar<8;bar++){
   uint64_t sums[4]={0};uint32_t counts[4]={0};
   for(unsigned row=8;row<1216;row++)for(unsigned x=bar*204+8;x<(bar+1)*204-8;x++){
    const unsigned char *b=data+(size_t)row*f->plane_fmt[0].bytesperline+(x/4)*5;
    unsigned value=((unsigned)b[x%4]<<2)|((b[4]>>(2*(x%4)))&3),channel=(row%2)*2+(x%2);
    sums[channel]+=value;counts[channel]++;
   }
   printf("RAW_PATCH frame=%u bar=%u r=%.6f gr=%.6f gb=%.6f b=%.6f\n",frame,bar,(double)sums[0]/counts[0],(double)sums[1]/counts[1],(double)sums[2]/counts[2],(double)sums[3]/counts[3]);
  }
'''+needle)
 source=ROOT/f'samurai-pattern-{name}.c';assert not source.exists();source.write_text(s)
 binary=host.PRIVATE/f'pattern-{name}-aarch64-private';assert not binary.exists()
 q=subprocess.run(['aarch64-linux-gnu-gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-static','-s','-I/mnt/e/edk2-samurai-out/kernel288/host-uapi/include',str(source),'-o',str(binary)],capture_output=True)
 (host.PRIVATE/f'pattern-{name}-compile-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
 assert subprocess.run(['qemu-aarch64',str(binary),'--self-test'],capture_output=True,timeout=10).returncode==0
 assert subprocess.run(['qemu-aarch64',str(binary),'--pattern','/tmp/wrong-kernel-pattern'],capture_output=True,timeout=10).returncode==3
 reports[name]=dict(binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),binary_bytes=binary.stat().st_size,
  source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),qemu_self_test_pass=True,wrong_kernel_guard_passed=True)
(ROOT/'pattern-tool-validation.json').write_text(json.dumps(dict(stage=291,tools=reports,sensor_pattern=2,csid_pattern=0,physical_csi=True,no_userspace_mmio=True),indent=2)+'\n')
print(json.dumps(reports,indent=2))
