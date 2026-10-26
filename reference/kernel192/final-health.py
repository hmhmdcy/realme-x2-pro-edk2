from pathlib import Path
import dbus,hashlib,json,os,subprocess
os.umask(0o077);out=Path('/var/lib/samurai/k192-final-health-r3');out.mkdir(mode=0o700)
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes();assert boot==Path('/var/lib/samurai/k189r2-reboot-runtime/boot-id-private.txt').read_bytes()
(out/'boot-id-private.txt').write_bytes(boot)
base=json.loads(Path('/var/lib/samurai/k192-baseline/summary.json').read_text())
log=subprocess.check_output(['dmesg'],text=True);(out/'dmesg-private.txt').write_text(log)
faults={k:log.count(v) for k,v in dict(warning='WARNING:',oops='Oops:',gpu='gpu fault:',slpi_fatal='fatal error received',bluetooth='Frame reassembly failed').items()}
assert faults==base['fault_counts']
rp={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')};assert rp==base['remoteprocs']
bus=dbus.SystemBus(private=True);props=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1/Modem/0'),'org.freedesktop.DBus.Properties')
power=int(props.Get('org.freedesktop.ModemManager1.Modem','PowerState'));loc=int(props.Get('org.freedesktop.ModemManager1.Modem.Location','Enabled'));assert power==3 and loc==0
sha=hashlib.sha256(Path('/usr/bin/ModemManager').read_bytes()).hexdigest();assert sha=='b350c55ba334b7d23564136fe3ce19bf37f95db0d374f63cc89351341d9b9ddc'
proxy=dbus.Interface(bus.get_object('net.hadess.SensorProxy','/net/hadess/SensorProxy'),'org.freedesktop.DBus.Properties')
sensors={name:bool(proxy.Get('net.hadess.SensorProxy',name)) for name in ['HasAccelerometer','HasAmbientLight','HasProximity']};assert all(sensors.values())
reg=[]
for p in Path('/sys/class/regulator').glob('regulator.*'):
 node=p/'of_node'
 if not node.exists():node=p/'device/of_node'
 if not node.exists() or node.resolve().name not in ['smps8','ldo1']:continue
 parent=node.resolve().parent
 if not (parent/'qcom,pmic-id').is_file() or (parent/'qcom,pmic-id').read_bytes().rstrip(b'\0')!=b'c':continue
 values={n:(p/n).read_text().strip() for n in ['name','state','microvolts','num_users'] if (p/n).is_file()}
 reg.append(dict(of_name=node.resolve().name,**values))
assert len([r for r in reg if r['of_name']=='smps8' and r['state']=='enabled' and r['microvolts']=='1352000'])==1
summary=dict(stage=192,same_boot_as189=True,kernel_build=183,taint=int(Path('/proc/sys/kernel/tainted').read_text()),remoteprocs=rp,fault_counts=faults,new_faults_since192_baseline=False,mm_power_state=power,location_enabled=loc,modemmanager191_unchanged=True,sensor_proxy=sensors,pmic_c_supplies=reg,physical_sensor_id_read=False,physical_camera_accepted=False)
assert summary['taint']==0
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');bus.close();print(json.dumps(summary))
