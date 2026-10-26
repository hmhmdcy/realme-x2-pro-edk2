"""Observe the new driver and normal heap autoload without starting capture."""
from pathlib import Path
import dbus,fcntl,grp,hashlib,json,os,stat,struct,subprocess
os.umask(0o077);root=Path('/var/lib/samurai');before=root/'k212-before-reboot';out=root/'k212-runtime'
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes();assert boot!=(before/'boot-id-private.txt').read_bytes() and os.uname().version.startswith('#183 ')
if out.exists():assert (out/'boot-id-private.txt').read_bytes()==boot
else:out.mkdir(mode=0o700);(out/'boot-id-private.txt').write_bytes(boot)
persist=json.loads((root/'k200-runtime/partition-hashes-private.json').read_text())['persist']
for dev,label,size,digest in [('sde11','boot',100663296,'c3bf043f2eea0c5f8e42cc8cac621ccfba023b181e400d0919174b87e3d37ba6'),('sde32','logdump',67108864,'e73754c7d327925acf031aed54e0e6d02069b7a112c32b187ac9bfb468da1358'),('sda2','persist',None,persist)]:
    p='/dev/'+dev;assert subprocess.check_output(['lsblk','-ndo','PARTLABEL',p],text=True).strip()==label
    if size:assert int(subprocess.check_output(['blockdev','--getsize64',p],text=True))==size
    assert subprocess.check_output(['sha256sum',p],text=True).split()[0]==digest,label
for args,name in [(['sha256sum','-c',str(before/'userspace-check.sha256')],'product'),(['sha256sum','-c',str(before/'module-tree.sha256')],'modules'),(['sha256sum','-c','/run/samurai-wifi/nv-source-hashes.txt'],'nv')]:
    with (out/(name+'-check-private.txt')).open('wb') as log:subprocess.run(args,cwd=Path('/usr/lib/modules')/os.uname().release,check=True,stdout=log,stderr=subprocess.STDOUT)
sensor=Path('/sys/bus/i2c/devices/7-0010');assert (sensor/'driver').resolve().name=='imx471'
assert (sensor/'of_node/power-domains').read_bytes()==Path('/sys/bus/platform/devices/ac4b000.cci/of_node/power-domains').read_bytes()
genpd=Path('/sys/kernel/debug/pm_genpd/pm_genpd_summary').read_text();(out/'sensor-domain-genpd-private.txt').write_text(genpd)
assert '7-0010' in genpd
installed=Path('/usr/lib/modules')/os.uname().release/'kernel/drivers/media/i2c/imx471.ko'
assert hashlib.sha256(installed.read_bytes()).hexdigest()=='a28dd67a03afa9e918f87b85030f0158edecbcc2e3f1ce0a36405b78be70ba6a'
def section(data,name):
    assert data[:6]==b'\x7fELF\x02\x01';offset=struct.unpack_from('<Q',data,40)[0];size,count,strings=struct.unpack_from('<HHH',data,58)
    headers=[struct.unpack_from('<IIQQQQIIQQ',data,offset+i*size) for i in range(count)];header=headers[strings];names=data[header[4]:header[4]+header[5]]
    for h in headers:
        if names[h[0]:].split(b'\0',1)[0]==name.encode():return data[h[4]:h[4]+h[5]]
    raise AssertionError('Missing ELF note')
assert section(installed.read_bytes(),'.note.gnu.build-id')==Path('/sys/module/imx471/notes/.note.gnu.build-id').read_bytes()
nodes=[p for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().strip()=='imx471 7-0010'];assert len(nodes)==1
fd=os.open('/dev/'+nodes[0].name,os.O_RDWR|os.O_CLOEXEC);selection={}
try:
    for which,label in [(0,'try'),(1,'active')]:
        selection[label]={}
        for target,name in [(0,'crop'),(1,'crop_default'),(2,'crop_bounds'),(3,'native_size'),(65535,'unsupported')]:
            buf=bytearray(64);struct.pack_into('4I',buf,0,which,0,target,0)
            try:fcntl.ioctl(fd,0xc040563d,buf,True);selection[label][name]=dict(success=True,rect=list(struct.unpack_from('4i',buf,16)))
            except OSError as error:selection[label][name]=dict(success=False,errno=error.errno)
finally:os.close(fd)
for label in selection:
    assert selection[label]['crop']==dict(success=True,rect=[8,408,4640,2644])
    assert selection[label]['crop_default']==dict(success=True,rect=[8,8,4656,3496])
    assert selection[label]['crop_bounds']==selection[label]['crop_default']
    assert selection[label]['native_size']==dict(success=True,rect=[0,0,4672,3512])
    assert selection[label]['unsupported']==dict(success=False,errno=22)
heaps=[];video_gid=grp.getgrnam('video').gr_gid
for p in Path('/dev/dma_heap').glob('*'):
    st=p.stat();heaps.append(dict(name=p.name,mode=oct(stat.S_IMODE(st.st_mode)),uid=st.st_uid,gid=st.st_gid))
    if p.name=='fastrpc-shared-pool':assert st.st_uid==st.st_gid==0 and stat.S_IMODE(st.st_mode)==0o600
    elif p.name in ['system','reserved','default_cma_region']:assert st.st_uid==0 and st.st_gid==video_gid and stat.S_IMODE(st.st_mode)==0o660
assert {'system','reserved','default_cma_region','fastrpc-shared-pool'}<={x['name'] for x in heaps}
assert all(Path('/sys/module'/Path(n)).exists() for n in ['system_heap','cma_heap','qcom_camss','i2c_qcom_cci','qcom_pm8008','qcom_pm8008_regulator','imx471','v4l2_cci'])
media=subprocess.run(['media-ctl','-d','/dev/media0','-p'],capture_output=True);(out/'media-graph-private.txt').write_bytes(media.stdout+media.stderr);assert media.returncode==0 and b'imx471 7-0010' in media.stdout
bus=dbus.SystemBus(private=True);owners={n:bool(bus.name_has_owner(n)) for n in ['org.bluez','org.freedesktop.ModemManager1','org.freedesktop.GeoClue2']}
loc={};modem={};bt_adapters=[];bt_connections=None
if owners['org.freedesktop.ModemManager1']:
    objects=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects();paths=[p for p,v in objects.items() if 'org.freedesktop.ModemManager1.Modem' in v]
    if len(paths)==1:
        props=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1',paths[0]),'org.freedesktop.DBus.Properties');loc=props.GetAll('org.freedesktop.ModemManager1.Modem.Location');modem=props.GetAll('org.freedesktop.ModemManager1.Modem')
if owners['org.bluez']:
    objects=dbus.Interface(bus.get_object('org.bluez','/'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects();bt_adapters=[dict(powered=bool(v['org.bluez.Adapter1']['Powered']),discovering=bool(v['org.bluez.Adapter1']['Discovering'])) for v in objects.values() if 'org.bluez.Adapter1' in v];bt_connections=sum(bool(v.get('org.bluez.Device1',{}).get('Connected',False)) for v in objects.values())
bus.close()
log=subprocess.check_output(['dmesg']);(out/'dmesg-private.txt').write_bytes(log)
faults={k:log.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()}
rp={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')}
report=dict(stage=212,new_boot_identity_verified=True,boot211_logdump183_persist_nv_readback_exact=True,installed_786_file_module_tree_exact=True,heap_configs_and_product_helpers_exact=True,patched_sensor_module_loaded_note_matches_installed=True,selection=selection,heap_devices=heaps,heaps_loaded_automatically=True,dedicated_dsp_pool_root_only=True,static_camera_bound=True,sensor_titan_top_domain_attached=True,media_entities=media.stdout.count(b'entity '),sensor_runtime_status=(sensor/'power/runtime_status').read_text().strip(),taint=int(Path('/proc/sys/kernel/tainted').read_text()),fault_counts=faults,remoteprocs=rp,dbus_owners=owners,gps_enabled=int(loc['Enabled']) if loc else None,signals_location=bool(loc['SignalsLocation']) if loc else None,gps_refresh_rate=int(loc['GpsRefreshRate']) if loc else None,bt_adapters=bt_adapters,bt_connections=bt_connections,partitions_flashed=[],camera_stream_not_started=True,same_boot211_image_second_warm_boot=True,uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]))
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
