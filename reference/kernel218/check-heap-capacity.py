from pathlib import Path
import host,json

here=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import json,os,pwd,resource,subprocess
root=Path('/var/lib/samurai');out=root/'k218-system-heap-capacity'
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k218-baseline/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert not out.exists();out.mkdir(mode=0o700)
def mem():return {l.split(':')[0]:int(l.split()[1])*1024 for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith(('MemAvailable:','CmaFree:','CmaTotal:'))}
before_mem=mem();before=subprocess.check_output(['dmesg'])
child=r"""
from pathlib import Path
import fcntl,json,mmap,os,struct
heap=os.open('/dev/dma_heap/system',os.O_RDWR|os.O_CLOEXEC);buffers=[];maps=[]
try:
    sizes=[5760*3456]*4+[4608*3456*4]*4
    exporters=[]
    for size in sizes:
        request=bytearray(struct.pack('QIIQ',size,0,os.O_RDWR|os.O_CLOEXEC,0))
        fcntl.ioctl(heap,0xc0184800,request,True)
        fd=struct.unpack('QIIQ',request)[1];buffers.append(fd)
        info=Path('/proc/self/fdinfo',str(fd)).read_text()
        exporter=[l.split(':',1)[1].strip() for l in info.splitlines() if l.startswith('exp_name:')]
        assert exporter==['system'];exporters+=exporter
        fcntl.ioctl(fd,0x40086200,struct.pack('Q',3)) # DMA_BUF_SYNC_START|RW
        mapping=mmap.mmap(fd,size,flags=mmap.MAP_SHARED,prot=mmap.PROT_READ|mmap.PROT_WRITE);maps.append(mapping)
        mapping[:16]=b'quad218capacity!';mapping[-16:]=b'quad218capacity!'
        assert mapping[:16]==mapping[-16:]==b'quad218capacity!'
        fcntl.ioctl(fd,0x40086200,struct.pack('Q',7)) # DMA_BUF_SYNC_END|RW
    print(json.dumps(dict(allocated_together=len(buffers),total_buffer_bytes=sum(sizes),all_exporters_system=True,
                          four_raw10_full_and_four_rgba_full=True,all_buffers_cpu_mapped_and_synced=True)))
finally:
    for mapping in maps:mapping.close()
    for fd in buffers:os.close(fd)
    os.close(heap)
"""
def demote():
    resource.setrlimit(resource.RLIMIT_AS,(768*1024*1024,768*1024*1024));resource.setrlimit(resource.RLIMIT_CPU,(15,15));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    user=pwd.getpwuid(10000);os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
p=subprocess.run(['python3','-c',child],preexec_fn=demote,capture_output=True,timeout=30)
(out/'stdout.json').write_bytes(p.stdout);(out/'stderr-private.log').write_bytes(p.stderr)
assert p.returncode==0
test=json.loads(p.stdout);after=subprocess.check_output(['dmesg'])
faults={k:after.count(v)-before.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()}
assert not any(faults.values()) and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
report=dict(stage=218,test=test,run_uid=10000,heaps_present=[p.name for p in Path('/dev/dma_heap').iterdir()],
            before_memory_bytes=before_mem,after_release_memory_bytes=mem(),
            no_camera_or_gpu_started=True,not_a_camss_import_or_full_sensor_capture_test=True,
            all_test_allocations_closed=True,taint=0,fault_counts=faults)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=60)
(host.PRIVATE/'heap-capacity-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);(here/'heap-capacity-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
