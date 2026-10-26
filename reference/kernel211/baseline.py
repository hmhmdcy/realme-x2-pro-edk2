from pathlib import Path
import dbus,fcntl,hashlib,json,os,stat,struct,subprocess
os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k211-baseline';out.mkdir(mode=0o700)
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes();assert boot==(root/'k210-runtime/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#183 ') and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
(out/'boot-id-private.txt').write_bytes(boot)
assert all(not Path('/sys/module'/Path(n)).exists() for n in ['samurai_front_overlay','samurai_vio_phandle','samurai_cci_bringup','samurai_camera_perf'])
for p in ['/sys/bus/i2c/devices/7-0010','/sys/bus/platform/devices/acb3000.camss','/sys/bus/platform/devices/ac4b000.cci']:
    assert Path(p,'power/runtime_status').read_text().strip()=='suspended'
modules=Path('/usr/lib/modules')/os.uname().release;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
expected=json.loads((root/'k210-module-install/module-inventory-after-private.json').read_text())
assert expected=={str(p.relative_to(modules)):sha(p) for p in modules.rglob('*') if p.is_file()}
heap_modules={}
for name in ['system_heap','cma_heap']:
    p=subprocess.run(['modinfo','-n',name],capture_output=True,text=True);assert p.returncode==0;path=Path(p.stdout.strip())
    heap_modules[name]=dict(installed=True,loaded=Path('/sys/module'/Path(name)).exists(),sha256=sha(path),path=str(path),depends=subprocess.check_output(['modinfo','-F','depends',name],text=True).strip())
heaps=[]
for p in Path('/dev/dma_heap').glob('*'):
    st=p.stat();heaps.append(dict(name=p.name,mode=oct(stat.S_IMODE(st.st_mode)),uid=st.st_uid,gid=st.st_gid))
nodes=[p for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().strip()=='imx471 7-0010'];assert len(nodes)==1
fd=os.open('/dev/'+nodes[0].name,os.O_RDWR|os.O_CLOEXEC);selection={}
try:
    for target,name in [(0,'crop'),(1,'crop_default'),(2,'crop_bounds'),(3,'native_size')]:
        buf=bytearray(64);struct.pack_into('4I',buf,0,1,0,target,0)
        try:fcntl.ioctl(fd,0xc040563d,buf,True);selection[name]=dict(success=True,rect=list(struct.unpack_from('4i',buf,16)))
        except OSError as error:selection[name]=dict(success=False,errno=error.errno)
finally:os.close(fd)
config={}
for path in ['/etc/init.d/modules','/etc/modules','/etc/init.d/udev','/etc/mdev.conf','/etc/udev/rules.d','/usr/lib/udev/rules.d','/lib/udev/rules.d','/etc/modules-load.d']:
    p=Path(path)
    if p.is_file():config[path]=p.read_text(errors='replace')
    elif p.is_dir():
        config[path]={str(f.relative_to(p)):f.read_text(errors='replace') for f in p.glob('*') if f.is_file() and (p.name=='modules-load.d' or any(x in f.read_text(errors='replace') for x in ['dma_heap','DMA_HEAP','SUBSYSTEM=="video4linux"']))}
(out/'loader-and-rules-private.json').write_text(json.dumps(config,indent=2)+'\n')
runlevels=[str(p.relative_to('/etc/runlevels')) for p in Path('/etc/runlevels').glob('*/*') if p.name in ['modules','udev','mdev']]
bus=dbus.SystemBus(private=True);props=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1/Modem/0'),'org.freedesktop.DBus.Properties');loc=props.GetAll('org.freedesktop.ModemManager1.Modem.Location')
assert int(loc['Enabled'])==0 and not loc['SignalsLocation'] and int(loc['GpsRefreshRate'])==30 and not bus.name_has_owner('org.freedesktop.GeoClue2')
objects=dbus.Interface(bus.get_object('org.bluez','/'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects();adapters=[v['org.bluez.Adapter1'] for v in objects.values() if 'org.bluez.Adapter1' in v]
assert len(adapters)==1 and not adapters[0]['Powered'] and not adapters[0]['Discovering'] and not any(v.get('org.bluez.Device1',{}).get('Connected',False) for v in objects.values());bus.close()
log=subprocess.check_output(['dmesg']);(out/'dmesg-private.txt').write_bytes(log)
faults={k:log.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()};assert not any(faults.values())
rp={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')};assert len(rp)==3 and all(v=='running' for v in rp.values())
report=dict(stage=211,same210_boot_verified=True,taint=0,fault_counts=faults,remoteprocs=rp,camera_rails_and_controller_idle=True,installed_786_file_module_tree_exact=True,heap_modules=heap_modules,heap_devices=heaps,selection=selection,runlevel_loaders=runlevels,udev_running=subprocess.run(['pgrep','-x','udevd'],stdout=subprocess.DEVNULL).returncode==0,gps_enabled=0,bt_powered=False,bt_connections=0,uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]))
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
