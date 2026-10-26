from pathlib import Path
import dbus,hashlib,json,os,subprocess
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k247-runtime/boot-id-private.txt').read_bytes();base=r/'k247-nextboot';s=json.loads((base/'capture/state-private.json').read_text());a=json.loads((base/'capture/summary.json').read_text());p=Path('/proc',str(s['pid']));alive=p.exists() and p.joinpath('stat').read_text().split()[21]==s['start_ticks'];assert s['terminal'] and s['exit_code']==0 and not alive and a['closed']
stale=[]
for name in ['started','starting','stopping','inactive','failed','wasinactive']:
 p=Path('/run/openrc')/name/'samurai-diag247'
 if p.is_symlink():assert p.resolve()==Path('/etc/init.d/samurai-diag247');p.unlink();stale.append(name)
loc_workers=[]
for p in Path('/proc').iterdir():
 if p.name.isdigit():
  try:
   if (p/'comm').read_text().strip()=='loc-session':loc_workers.append(int(p.name))
  except OSError:pass
assert not loc_workers;assert a['memshare']['socket_closed'] and a['memshare']['withdrawal_sent'] and not a['memshare']['error']
query_state=json.loads((r/'k247-configured-query/state-private.json').read_text());assert query_state['terminal'] and query_state['exit_code']==0 and not Path('/proc',str(query_state['pid'])).exists() and query_state['memshare']['socket_closed'] and query_state['memshare']['withdrawal_sent'] and not query_state['memshare']['error']
x=subprocess.run(['sha256sum','-c','/run/samurai-wifi/nv-source-hashes.txt'],capture_output=True,timeout=20);assert x.returncode==0
services={}
for name,expected in [('rmtfs','d1ca1fc4087e47f1618e09f568605f2f253eac8721598fc930d1eb8c604fe251'),('tftp','b3bb82b9d090a5d06e9ba2ca24e3373ab1c1e7cc2a5c6b603e2acb02715487a1')]:
 pid=int(Path('/run/samurai-wifi',name+'.pid').read_text());p=Path('/proc',str(pid));digest=hashlib.sha256((p/'exe').read_bytes()).hexdigest();assert digest==expected
 if name=='tftp':assert b'SAMURAI_TFTP_RW_ROOT=/run/samurai-wifi/tftp-rw' in (p/'environ').read_bytes().split(b'\0')
 services[name]=dict(alive=True,sha256=digest)
queries={}
for label,option in [('lock','--loc-get-engine-lock'),('mode','--loc-get-operation-mode'),('dms','--dms-get-operating-mode')]:
 q=subprocess.run(['qmicli','-p','-d','qrtr://0',option],capture_output=True,timeout=15);assert q.returncode==0;queries[label]=q.stdout.decode().strip()
assert queries['lock']=='Successfully retrieved engine lock: mt'
bus=dbus.SystemBus(private=True);objects=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects();v=next(x for x in objects.values() if 'org.freedesktop.ModemManager1.Modem' in x);loc=v['org.freedesktop.ModemManager1.Modem.Location'];mm=v['org.freedesktop.ModemManager1.Modem'];watch=json.loads((r/'gnss-assist/watch-state.json').read_text());wlan=[]
for path in dbus.Interface(bus.get_object('org.freedesktop.NetworkManager','/org/freedesktop/NetworkManager'),'org.freedesktop.NetworkManager').GetDevices():
 p=dbus.Interface(bus.get_object('org.freedesktop.NetworkManager',str(path)),'org.freedesktop.DBus.Properties');value=p.GetAll('org.freedesktop.NetworkManager.Device')
 if int(value['DeviceType'])==2:wlan.append(int(value['State']))
bus.close();qrtr=subprocess.check_output(['qrtr-lookup']).decode();owned=[line for line in qrtr.splitlines() if len(line.split())>=5 and line.split()[0] in ['4097','52'] and line.split()[3]=='1'];assert not owned;dm=subprocess.check_output(['dmesg']).decode();faults={k:dm.count(v) for k,v in dict(warning='WARNING:',oops='Oops:',gpu='gpu fault:',dsp_fatal='fatal error received').items()};remote=[dict(name=(p/'name').read_text().strip(),state=(p/'state').read_text().strip()) for p in Path('/sys/class/remoteproc').glob('*')]
report=dict(stage=247,current_guard='k247-runtime',new_linux_boot=True,kernel_version=os.uname().version,diag_worker_terminal=True,diag_closed=a['closed'],both_phases_stop_release_close=all(all(p['cleanup'][k] for k in ['stop_ack','client_released','device_closed']) for p in a['phases']),mask_zero_reset_request_sent=a['mask_zero_reset_request_sent'],realtime_release_request_sent=a['realtime_release_request_sent'],local_diag_and_memshare_servers=0,memshare=a['memshare'],memshare_published_before_first_linux_modem_boot=a['memshare_published_before_first_linux_modem_boot'],temporary_hook_absent=not Path('/etc/init.d/samurai-diag247').exists() and not Path('/etc/runlevels/default/samurai-diag247').exists(),owned_stale_openrc_entries_removed=stale,no_loc_workers=True,original_nv_source_hashes_preserved=True,file_services=services,receiver_configuration=queries,mm_state=int(mm['State']),mm_power=int(mm['PowerState']),location_enabled=int(loc['Enabled']),signals_location=bool(loc['SignalsLocation']),gps_refresh=int(loc['GpsRefreshRate']),watch_running=watch['running'],assist_active=watch['active'],time_prepared=watch['time_prepared'],worker_starts=watch['worker_starts'],worker_completions=watch['worker_completions'],wlan_states=wlan,remoteprocs=remote,current_boot_fault_counts=faults,taint=int(Path('/proc/sys/kernel/tainted').read_text()))
assert all(report[k] for k in ['diag_closed','both_phases_stop_release_close','mask_zero_reset_request_sent','realtime_release_request_sent','temporary_hook_absent','no_loc_workers','original_nv_source_hashes_preserved','watch_running','time_prepared']) and report['taint']==0 and not any(faults.values()) and report['mm_power']==1 and report['location_enabled']==0 and not report['signals_location'] and report['gps_refresh']==30 and not report['assist_active'] and report['worker_starts']==report['worker_completions']==0 and 100 in wlan and all(x['state']=='running' for x in remote)
report['configured_query_reannouncement']=query_state
print(json.dumps({'report':report,'private':dict(dmesg=dm,qrtr=qrtr,watch=watch,nv_check=(x.stdout+x.stderr).decode())}))
