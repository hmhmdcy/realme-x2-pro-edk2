from pathlib import Path
import dbus,hashlib,json,os,subprocess
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k244-runtime/boot-id-private.txt').read_bytes()
attempts={}
for name,expected in [('k245-engine-lock',0),('k245-resume-rf',1),('k245-resume-rf-r2',1),('k245-resume-rf-r3',0),('k245-resume-rf-r4',0),('k245-memshare-observe',0)]:
 s=json.loads((r/name/'state-private.json').read_text());p=Path('/proc',str(s['pid']));alive=p.exists() and p.joinpath('stat').read_text().split()[21]==s['start_ticks'];assert s['terminal'] and s['exit_code']==expected and not alive;attempts[name]=dict(terminal=True,expected_exit_code=expected,worker_alive=False)
loc_workers=[]
for p in Path('/proc').iterdir():
 if p.name.isdigit():
  try:
   if (p/'comm').read_text().strip()=='loc-session':loc_workers.append(int(p.name))
  except OSError:pass
assert not loc_workers
check=subprocess.run(['sha256sum','-c','/run/samurai-wifi/nv-source-hashes.txt'],capture_output=True,timeout=20);assert check.returncode==0
services={}
for name,expected in [('rmtfs','d1ca1fc4087e47f1618e09f568605f2f253eac8721598fc930d1eb8c604fe251'),('tftp','b3bb82b9d090a5d06e9ba2ca24e3373ab1c1e7cc2a5c6b603e2acb02715487a1')]:
 pid=int(Path('/run/samurai-wifi',name+'.pid').read_text());p=Path('/proc',str(pid));digest=hashlib.sha256((p/'exe').read_bytes()).hexdigest();assert digest==expected
 if name=='tftp':assert b'SAMURAI_TFTP_RW_ROOT=/run/samurai-wifi/tftp-rw' in (p/'environ').read_bytes().split(b'\0')
 services[name]=dict(alive=True,sha256=digest)
lock=subprocess.run(['qmicli','-p','-d','qrtr://0','--loc-get-engine-lock'],capture_output=True,timeout=15);assert lock.returncode==0 and lock.stdout.decode().strip()=='Successfully retrieved engine lock: mt'
bus=dbus.SystemBus(private=True);objects=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects();v=next(x for x in objects.values() if 'org.freedesktop.ModemManager1.Modem' in x);loc=v['org.freedesktop.ModemManager1.Modem.Location'];modem=v['org.freedesktop.ModemManager1.Modem'];watch=json.loads((r/'gnss-assist/watch-state.json').read_text());wlan=[]
for path in dbus.Interface(bus.get_object('org.freedesktop.NetworkManager','/org/freedesktop/NetworkManager'),'org.freedesktop.NetworkManager').GetDevices():
 p=dbus.Interface(bus.get_object('org.freedesktop.NetworkManager',str(path)),'org.freedesktop.DBus.Properties');a=p.GetAll('org.freedesktop.NetworkManager.Device')
 if int(a['DeviceType'])==2:wlan.append(int(a['State']))
assert not bus.name_has_owner('org.freedesktop.GeoClue2');bus.close();qrtr=subprocess.check_output(['qrtr-lookup']).decode();owned=[]
for line in qrtr.splitlines():
 p=line.split()
 if len(p)>=5 and p[0] in ['52','4097'] and p[3]=='1':owned.append(p)
assert not owned;dm=subprocess.check_output(['dmesg']).decode();faults={k:dm.count(v) for k,v in dict(warning='WARNING:',oops='Oops:',gpu='gpu fault:',dsp_fatal='fatal error received').items()};remoteprocs=[dict(name=(p/'name').read_text().strip(),state=(p/'state').read_text().strip()) for p in Path('/sys/class/remoteproc').glob('*')]
report=dict(stage=245,current_guard='k244-runtime',same_linux_boot=True,kernel_version=os.uname().version,worker_attempts=attempts,no_loc_workers=True,engine_lock='mt',original_nv_source_hashes_unchanged=True,file_services=services,local_diag_and_memshare_servers=0,mm_state=int(modem['State']),mm_power=int(modem['PowerState']),location_enabled=int(loc['Enabled']),signals_location=bool(loc['SignalsLocation']),gps_refresh=int(loc['GpsRefreshRate']),watch_running=watch['running'],assist_active=watch['active'],time_prepared=watch['time_prepared'],worker_starts=watch['worker_starts'],worker_completions=watch['worker_completions'],remoteprocs=remoteprocs,wlan_states=wlan,current_boot_fault_counts=faults,taint=int(Path('/proc/sys/kernel/tainted').read_text()),no_reboot_or_flash_this_stage=True)
assert report['taint']==0 and not any(faults.values()) and all(x['state']=='running' for x in remoteprocs) and report['location_enabled']==0 and not report['signals_location'] and report['gps_refresh']==30 and not report['assist_active'] and report['time_prepared'] and report['worker_starts']==report['worker_completions']==0 and report['mm_power']==1 and 100 in wlan
print(json.dumps({'report':report,'private':dict(dmesg=dm,qrtr=qrtr,watch=watch,nv_check=(check.stdout+check.stderr).decode())}))
