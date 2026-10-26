"""Prepare a read-only register diagnostic owned by the live V4L2 capture."""
from pathlib import Path
import hashlib,json,subprocess
ROOT=Path(__file__).resolve().parent;PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel294')
s=(ROOT/'samurai-stats.c').read_text()
insert=r'''
static int readback(unsigned frame) {
 const char *node="/sys/bus/platform/devices/acb3000.camss/";
 char path[256];unsigned char reg[160];
 snprintf(path,sizeof(path),"%sof_node/reg",node);int fd=open(path,O_RDONLY|O_CLOEXEC);if(fd<0)return -1;
 ssize_t length=read(fd,reg,sizeof(reg));close(fd);if(length!=160){errno=EPROTO;return -1;}
 uint64_t base=0,size=0;for(unsigned i=0;i<8;i++){base=(base<<8)|reg[96+i];size=(size<<8)|reg[104+i];}
 if(base!=0xacaf000||size!=0x4000){errno=EPROTO;return -1;}
 snprintf(path,sizeof(path),"%spower/runtime_status",node);fd=open(path,O_RDONLY|O_CLOEXEC);if(fd<0)return -1;
 char pm[32]={0};length=read(fd,pm,sizeof(pm)-1);close(fd);if(length<0||strcmp(pm,"active\n")){errno=EHOSTDOWN;return -1;}
 fd=open("/dev/mem",O_RDONLY|O_SYNC|O_CLOEXEC);if(fd<0)return -1;
 volatile uint32_t *mm=mmap(NULL,size,PROT_READ,MAP_SHARED,fd,base);if(mm==MAP_FAILED){close(fd);return -1;}
 const unsigned offsets[]={0x0,0xc,0x30,0x44,0xaac,0xbe4,0xbe8,0x200c,0x2014,0x2084,0x2044,0x205c,0x2060,0x3200,0x3204,0x3208,0x3214,0x3218,0x321c,0x3220,0x3224,0x3228,0x3248,0x324c,0x3250,0x3254,0x3258,0x325c};
 printf("READBACK frame=%u",frame);
 for(unsigned i=0;i<sizeof(offsets)/sizeof(offsets[0]);i++){uint32_t value=mm[offsets[i]/4];__sync_synchronize();printf(" r%04x=%08x",offsets[i],value);}
 puts("");fflush(stdout);munmap((void*)mm,size);close(fd);return 0;
}
'''
s=s.replace('static int stats_dequeue(',insert+'\nstatic int stats_dequeue(',1)
s=s.replace('  if(stats_streaming&&stats_dequeue(frame,argv[2]))goto cleanup;','  if(stats_streaming&&stats_dequeue(frame,argv[2]))goto cleanup;\n  if(frame%9==8&&readback(frame))goto cleanup;')
p=ROOT/'samurai-stats-readback.c';assert not p.exists();p.write_text(s)
binary=PRIVATE/'stats-readback-aarch64-private'
q=subprocess.run(['aarch64-linux-gnu-gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-D__counted_by(x)=','-D__EXPORTED_HEADERS__','-static','-s','-I/mnt/e/edk2-samurai-out/kernel288/host-uapi/include','-I/home/cy122/x2pro-linux/camera279-isp-kernel/include/uapi',str(p),'-o',str(binary)],capture_output=True)
(PRIVATE/'stats-readback-compile-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
assert subprocess.run(['qemu-aarch64',str(binary),'--self-test'],capture_output=True,timeout=10).returncode==0
assert subprocess.run(['qemu-aarch64',str(binary),'--pattern','/tmp/wrong-kernel'],capture_output=True,timeout=10).returncode==3
(ROOT/'stats-readback-tool-validation.json').write_text(json.dumps(dict(stage=294,binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),binary_bytes=binary.stat().st_size,strict_compile_pass=True,wrong_kernel_guard_pass=True,readonly_mmio=True,mmio_live_stream_and_dt_checked=True,not_run_on_phone=True),indent=2)+'\n')
for source,target in [('native-stats.py','native-stats-readback.py'),('launch-stats.py','launch-stats-readback.py'),('poll-stats.py','poll-stats-readback.py')]:
 s=(ROOT/source).read_text().replace('stats','stats-readback')
 # Replacing all text would corrupt field names and Python identifiers.
 s=(ROOT/source).read_text()
 for a,b in [('k294-stats-r1','k294-stats-readback-r1'),('k294-tools/stats','k294-tools/stats-readback'),('native-stats.py','native-stats-readback.py'),("'stats-tool-validation.json'","'stats-readback-tool-validation.json'"),("'stats-aarch64-private'","'stats-readback-aarch64-private'"),('stats-launch-private.json','stats-readback-launch-private.json'),('stats-poll-private.json','stats-readback-poll-private.json'),('stats-capture-validation.json','stats-readback-capture-validation.json'),('stats-worker-private.log','stats-readback-worker-private.log')]:s=s.replace(a,b)
 if source.startswith('native-'):s=s.replace('no_userspace_mmio=True','no_userspace_mmio=False,readonly_mmio_diagnostic=True')
 p=ROOT/target;assert not p.exists();compile(s,str(p),'exec');p.write_text(s)
print('Prepared read-only diagnostic; kernel source and installed payload unchanged.')
