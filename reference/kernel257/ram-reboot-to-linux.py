"""One normal restart from the verified RAM restore environment."""
from pathlib import Path
import os,json,struct,mmap,ctypes,time
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/run/k257-rescue-boot-id-private.txt').read_bytes()
assert os.uname().machine=='aarch64' and os.uname().version.startswith('#183 ')
state=json.loads(Path('/run/k257-restore/state.json').read_text())
assert state['terminal'] and state['exit_code']==0 and state['state']=='complete'
summary=json.loads(Path('/run/k257-restore/summary.json').read_text())
assert summary['original_linux_root_marker_sha_matches'] and summary['fsck_dry_run_exit_code']==0
assert Path('/sys/class/block/sda16/ro').read_text().strip()=='1'
assert not any(line.split()[0]=='/dev/sda16' for line in Path('/proc/mounts').read_text().splitlines())
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert all((p/'state').read_text().strip()=='offline' for p in Path('/sys/class/remoteproc').glob('*'))
assert all('active=1' not in p.read_text() for p in Path('/sys/kernel/debug/dri').glob('*/state'))
device=Path('/sys/bus/platform/devices/88e0000.serial')
assert (device/'driver').resolve()==Path('/sys/bus/platform/drivers/qcom_eud_com')
assert (device/'of_node/reg').read_bytes()==struct.pack('>IIII',0,0x088e0000,0,0x2000)
assert (device/'of_node/compatible').read_bytes()==b'qcom,sm8150-eud-com\0'
assert os.sysconf('SC_PAGE_SIZE')==4096
phase=Path('/run/k257-normal-reboot-transaction.json');assert not phase.exists()
fd=os.open('/dev/mem',os.O_RDWR|os.O_SYNC)
try:
    with mmap.mmap(fd,4096,flags=mmap.MAP_SHARED,prot=mmap.PROT_READ|mmap.PROT_WRITE,offset=0x088e1000) as csr:
        before=struct.unpack_from('<I',csr,0x14)[0];assert before&255 in [0,1]
        phase.write_text(json.dumps(dict(stage=257,request_count=1,state='before_eud_retirement_normal_restart'))+'\n')
        os.sync()
        Path('/sys/bus/platform/drivers/qcom_eud_com/unbind').write_text(device.name)
        assert not (device/'driver').exists()
        struct.pack_into('<I',csr,0x14,0);assert struct.unpack_from('<I',csr,0x14)[0]&255==0
        phase.write_text(json.dumps(dict(stage=257,request_count=1,state='before_single_normal_restart',eud_console_unbound=True,eud_disable_readback=True))+'\n')
        print(json.dumps(dict(normal_restart_requested_once=True,restored_userdata_unmounted_and_readonly=True,eud_retired=True)),flush=True)
    time.sleep(.5)
    libc=ctypes.CDLL(None,use_errno=True);libc.syscall.restype=ctypes.c_long
    libc.syscall.argtypes=[ctypes.c_long,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_void_p]
    result=libc.syscall(142,0xfee1dead,672274793,0x01234567,None)
    raise RuntimeError('Normal restart returned: '+str((result,ctypes.get_errno())))
finally:os.close(fd)
