"""Observe boot210 and static camera binding without manual probe or stream."""
from pathlib import Path
import dbus,hashlib,json,os,subprocess
os.umask(0o077)
root=Path('/var/lib/samurai');before=root/'k210-before-reboot';out=root/'k210-runtime'
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot!=(before/'boot-id-private.txt').read_bytes() and os.uname().version.startswith('#183 ')
assert Path('/sys/firmware/devicetree/base/model').read_bytes()==b'Realme X2 Pro (RMX1931CN)\0'
if out.exists():assert (out/'boot-id-private.txt').read_bytes()==boot
else:
    out.mkdir(mode=0o700);(out/'boot-id-private.txt').write_bytes(boot)
persist=json.loads((root/'k200-runtime/partition-hashes-private.json').read_text())['persist']
for dev,label,size,digest in [('sde11','boot',100663296,'89242ade44ddaebf2b124d3bb5e9bd6597d0c818488b1e84d719d36a5a5023c0'),('sde32','logdump',67108864,'e73754c7d327925acf031aed54e0e6d02069b7a112c32b187ac9bfb468da1358'),('sda2','persist',None,persist)]:
    p='/dev/'+dev;assert subprocess.check_output(['lsblk','-ndo','PARTLABEL',p],text=True).strip()==label
    if size:assert int(subprocess.check_output(['blockdev','--getsize64',p],text=True))==size
    assert subprocess.check_output(['sha256sum',p],text=True).split()[0]==digest,label
for args,name in [(['sha256sum','-c',str(before/'userspace-check.sha256')],'userspace'),(['sha256sum','-c',str(before/'module-tree.sha256')],'modules'),(['sha256sum','-c','/run/samurai-wifi/nv-source-hashes.txt'],'nv')]:
    with (out/(name+'-check-private.txt')).open('wb') as log:subprocess.run(args,cwd=Path('/usr/lib/modules')/os.uname().release,check=True,stdout=log,stderr=subprocess.STDOUT)
dt=Path('/sys/firmware/devicetree/base');sensor_node=dt/'soc@0/cci@ac4b000/i2c-bus@1/camera@10';pmic_node=dt/'soc@0/geniqup@8c0000/i2c@890000/pmic@4'
assert sensor_node.exists() and pmic_node.exists() and (dt/'soc@0/cci@ac4b000/status').read_bytes()==b'okay\0'
def devices(node):
    result=[]
    for p in Path('/sys/bus/i2c/devices').iterdir():
        if (p/'of_node').exists() and (p/'of_node').resolve()==node:
            item=dict(device=p.name,bound=(p/'driver').exists(),driver=(p/'driver').resolve().name if (p/'driver').exists() else None)
            for prop in ['power/runtime_status','power/runtime_usage']:
                if (p/prop).exists():item[prop]=(p/prop).read_text().strip()
            result.append(item)
    return result
media={}
for p in Path('/dev').glob('media*'):
    q=subprocess.run(['media-ctl','-d',str(p),'-p'],capture_output=True,text=True,timeout=10);(out/(p.name+'-graph-private.txt')).write_text(q.stdout+q.stderr)
    media[p.name]=dict(exit=q.returncode,imx471='imx471' in q.stdout,entities=sum('entity ' in l for l in q.stdout.splitlines()))
rails=[]
for p in Path('/sys/class/regulator').glob('regulator.*'):
    name=(p/'name').read_text().strip()
    if name in ['cam-front-vdig','cam-front-vana']:
        r=dict(name=name)
        for prop in ['state','num_users','microvolts']:
            try:r[prop]=(p/prop).read_text().strip()
            except OSError as error:r[prop]=dict(errno=error.errno)
        rails.append(r)
for path,name in [('/sys/kernel/debug/gpio','gpio-private.txt'),('/sys/kernel/debug/clk/clk_summary','clocks-private.txt'),('/sys/kernel/debug/regulator/regulator_summary','regulators-private.txt')]:
    (out/name).write_bytes(Path(path).read_bytes())
bus=dbus.SystemBus(private=True)
mm_objects=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
modems=[p for p,v in mm_objects.items() if 'org.freedesktop.ModemManager1.Modem' in v]
assert len(modems)<=1
loc={};modem={}
if modems:
    props=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1',modems[0]),'org.freedesktop.DBus.Properties')
    loc=props.GetAll('org.freedesktop.ModemManager1.Modem.Location');modem=props.GetAll('org.freedesktop.ModemManager1.Modem')
objects=dbus.Interface(bus.get_object('org.bluez','/'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
adapters=[v['org.bluez.Adapter1'] for v in objects.values() if 'org.bluez.Adapter1' in v]
assert len(adapters)==1 and not adapters[0]['Powered'] and not adapters[0]['Discovering']
assert not any(v.get('org.bluez.Device1',{}).get('Connected',False) for v in objects.values());bus.close()
log=subprocess.check_output(['dmesg']);(out/'dmesg-private.txt').write_bytes(log)
faults={k:log.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()}
watch=json.loads((root/'gnss-assist/watch-state.json').read_text());(out/'watch-first-private.json').write_text(json.dumps(watch,indent=2)+'\n')
rp={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')}
report=dict(stage=210,new_boot_identity_verified=True,boot210_logdump183_persist_nv_readback_exact=True,installed_786_file_module_tree_exact=True,product_helpers_unchanged=True,camera_static_nodes_present=True,front_sensor=devices(sensor_node),pm8008=devices(pmic_node),media=media,front_rails=rails,modules={n:Path('/sys/module'/Path(n)).exists() for n in ['qcom_camss','i2c_qcom_cci','qcom_pm8008','qcom_pm8008_regulator','imx471','v4l2_cci']},temporary_helpers_loaded=any(Path('/sys/module'/Path(n)).exists() for n in ['samurai_cci_bringup','samurai_front_overlay','samurai_vio_phandle']),taint=int(Path('/proc/sys/kernel/tainted').read_text()),fault_counts=faults,remoteprocs=rp,modem_objects=len(modems),gps_enabled=int(loc['Enabled']) if loc else None,signals_location=bool(loc['SignalsLocation']) if loc else None,gps_refresh_rate=int(loc['GpsRefreshRate']) if loc else None,modem_power_state=int(modem['PowerState']) if modem else None,bt_powered=False,bt_connections=0,gnss_watcher_running=watch['running'],gnss_time_prepared=watch['time_prepared'],uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]),camera_stream_not_started=True)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
