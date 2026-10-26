"""Load installed DMA heaps and persist the normal OpenRC/udev integration."""
from pathlib import Path
import grp,hashlib,json,os,pwd,shutil,stat,subprocess,sys
os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k211-heaps-deploy';out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k211-baseline/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
stage=root/'k211-heap-stage';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
baseline=json.loads((root/'k211-baseline/summary.json').read_text())
assert not baseline['heap_devices'] and all(not x['loaded'] for x in baseline['heap_modules'].values())
for name,item in baseline['heap_modules'].items():assert not Path('/sys/module'/Path(name)).exists() and sha(Path(item['path']))==item['sha256']
assert not list(Path('/dev/dma_heap').glob('*'))
before_log=subprocess.check_output(['dmesg']);(out/'dmesg-before-private.txt').write_bytes(before_log)
destinations={'samurai-camera-heaps.conf':'/etc/modules-load.d/samurai-camera-heaps.conf','70-samurai-camera-heaps.rules':'/etc/udev/rules.d/70-samurai-camera-heaps.rules'}
backup={}
for name,destination in destinations.items():
    target=Path(destination);backup[destination]=dict(existed=target.exists())
    if target.exists():
        st=target.stat();backup[destination].update(sha256=sha(target),mode=stat.S_IMODE(st.st_mode));shutil.copyfile(target,out/(name+'.before-private'))
    else:assert not target.is_symlink()
(out/'rollback-private.json').write_text(json.dumps(backup,indent=2)+'\n')
manifest=json.loads((stage/'source-manifest.json').read_text())
for name,destination in destinations.items():
    assert sha(stage/name)==manifest[name];target=Path(destination);target.parent.mkdir(parents=True,exist_ok=True)
    temporary=target.with_name(target.name+'.k211-new');assert not temporary.exists();shutil.copyfile(stage/name,temporary);temporary.chmod(0o644);os.replace(temporary,target)
for i,args in enumerate([['udevadm','control','--reload-rules'],['modprobe','system_heap'],['modprobe','cma_heap'],['udevadm','settle','--timeout=10']]):
    p=subprocess.run(args,capture_output=True,timeout=20);(out/('command-'+str(i)+'-private.log')).write_bytes(p.stdout+p.stderr);assert p.returncode==0
heaps=[];video_gid=grp.getgrnam('video').gr_gid
for p in Path('/dev/dma_heap').glob('*'):
    st=p.stat();assert stat.S_ISCHR(st.st_mode) and st.st_uid==0 and st.st_gid==video_gid and stat.S_IMODE(st.st_mode)==0o660
    heaps.append(dict(name=p.name,mode='0660',group='video'))
assert any(p['name']=='system' for p in heaps)
# Allocate, map, synchronize and release our own 64KiB buffer as the actual user.
program=r'''
import fcntl,json,mmap,os,struct,sys
assert os.geteuid()==10000
results=[]
for name in sys.argv[1:]:
    heap=os.open('/dev/dma_heap/'+name,os.O_RDWR|os.O_CLOEXEC)
    try:
        buf=bytearray(struct.pack('QIIQ',65536,0,os.O_RDWR|os.O_CLOEXEC,0));fcntl.ioctl(heap,0xc0184800,buf,True);fd=struct.unpack_from('I',buf,8)[0]
        try:
            mapping=mmap.mmap(fd,65536,flags=mmap.MAP_SHARED,prot=mmap.PROT_READ|mmap.PROT_WRITE)
            try:
                fcntl.ioctl(fd,0x40086200,struct.pack('Q',3));mapping[:]=bytes(range(256))*256;assert mapping[:]==bytes(range(256))*256;fcntl.ioctl(fd,0x40086200,struct.pack('Q',7))
            finally:mapping.close()
        finally:os.close(fd)
        results.append(dict(heap=name,bytes=65536,allocate_map_cpu_sync_readback_close=True))
    finally:os.close(heap)
print(json.dumps(dict(uid=os.geteuid(),allocations=results)))
'''
user=pwd.getpwuid(10000)
def demote():os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
selected=[p['name'] for p in heaps if p['name'] in ['system','default_cma_region','linux,cma','reserved','default-pool']]
assert 'system' in selected
p=subprocess.run([sys.executable,'-c',program,*selected],preexec_fn=demote,cwd='/',capture_output=True,timeout=20)
(out/'user-allocation-private.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0
allocation=json.loads(p.stdout);assert len(allocation['allocations'])==len(selected)
after_log=subprocess.check_output(['dmesg']);(out/'dmesg-after-private.txt').write_bytes(after_log)
faults={k:after_log.count(v)-before_log.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()};assert not any(faults.values())
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert Path('/sys/bus/i2c/devices/7-0010/power/runtime_status').read_text().strip()=='suspended'
report=dict(stage=211,heap_modules_loaded=True,normal_openrc_modules_load_config_installed=True,video_group_uaccess_rule_installed=True,heap_devices=heaps,user_allocation=allocation,no_custom_allocator_or_fake_node_alias=True,sensor_stayed_suspended=True,taint=0,fault_delta=faults,reboot_persistence_not_yet_tested=True)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
