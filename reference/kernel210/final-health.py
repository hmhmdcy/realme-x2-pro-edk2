from pathlib import Path
import dbus,hashlib,json,os,re,subprocess
os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k210-final-health';out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k210-runtime/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#183 ')
capture=json.loads((root/'k210-static-front-capture-r3/summary.json').read_text());fixture=json.loads((root/'k210-capture-monitor-fixture-r3/summary.json').read_text())
assert capture['six_physical_raw10_frames_captured'] and capture['all_idle_rails_clocks_and_own_mmcx_votes_released'] and fixture['monitor_resumed']
sensor=Path('/sys/bus/i2c/devices/7-0010');camss=Path('/sys/bus/platform/devices/acb3000.camss');cci=Path('/sys/bus/platform/devices/ac4b000.cci')
assert (sensor/'driver').resolve().name=='imx471'
assert all((p/'power/runtime_status').read_text().strip()=='suspended' for p in [sensor,camss,cci])
rails={}
for p in Path('/sys/class/regulator').glob('regulator.*'):
    name=(p/'name').read_text().strip()
    if name in ['cam-front-vdig','cam-front-vana']:
        rails[name]={n:(p/n).read_text().strip() for n in ['state','num_users','microvolts']}
assert len(rails)==2 and all(x['state']=='disabled' and x['num_users']=='0' for x in rails.values())
clocks=Path('/sys/kernel/debug/clk/clk_summary').read_text();mclk=next(l.split() for l in clocks.splitlines() if re.search(r'\bcam_cc_mclk2_clk\s',l));assert int(mclk[1])==0
pd=Path('/sys/kernel/debug/pm_genpd/pm_genpd_summary').read_text();assert re.search(r'genpd:3:acb3000.camss\s+suspended\s+0\s',pd)
(out/'clock-private.txt').write_text(clocks);(out/'genpd-private.txt').write_text(pd)
bus=dbus.SystemBus(private=True);props=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1/Modem/0'),'org.freedesktop.DBus.Properties')
loc=props.GetAll('org.freedesktop.ModemManager1.Modem.Location');assert int(loc['Enabled'])==0 and not loc['SignalsLocation'] and int(loc['GpsRefreshRate'])==30
assert not bus.name_has_owner('org.freedesktop.GeoClue2')
objects=dbus.Interface(bus.get_object('org.bluez','/'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects();adapters=[v['org.bluez.Adapter1'] for v in objects.values() if 'org.bluez.Adapter1' in v]
assert len(adapters)==1 and not adapters[0]['Powered'] and not adapters[0]['Discovering'] and not any(v.get('org.bluez.Device1',{}).get('Connected',False) for v in objects.values());bus.close()
watch=json.loads((root/'gnss-assist/watch-state.json').read_text());(out/'watch-private.json').write_text(json.dumps(watch,indent=2)+'\n')
assert watch['running'] and not watch['active'] and watch['worker_starts']==watch['worker_completions']==0
chrony=subprocess.run(['chronyc','tracking'],capture_output=True,text=True,timeout=10);(out/'chrony-private.txt').write_text(chrony.stdout+chrony.stderr)
log=subprocess.check_output(['dmesg']);(out/'dmesg-private.txt').write_bytes(log)
faults={k:log.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()};assert not any(faults.values())
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
rp={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')};assert len(rp)==3 and all(v=='running' for v in rp.values())
for args,name in [(['sha256sum','-c','/run/samurai-wifi/nv-source-hashes.txt'],'nv'),(['sha256sum','-c',str(root/'k210-before-reboot/userspace-check.sha256')],'product')]:
    with (out/(name+'-check-private.txt')).open('wb') as log:subprocess.run(args,check=True,stdout=log,stderr=subprocess.STDOUT)
tools={n:subprocess.run(['sh','-c','command -v '+n],capture_output=True,text=True).returncode==0 for n in ['cam','qcam','gst-launch-1.0','pw-cli','wpctl']}
packages=subprocess.run(['apk','info'],capture_output=True,text=True,timeout=15);(out/'package-list-private.txt').write_text(packages.stdout+packages.stderr)
report=dict(stage=210,same_new_boot=True,static_front_still_bound=True,sensor_camss_cci_suspended=True,front_rails_disabled_zero_users=True,mclk_off_and_own_mmcx_vote_zero=True,wireplumber_resumed=True,gps_enabled=0,signals_location=False,gps_refresh_rate=30,bt_powered=False,bt_connections=0,gnss_watcher_idle=True,gnss_time_prepared=watch['time_prepared'],gnss_time_preparation_attempts=watch['time_preparation_starts'],chrony_normal=chrony.returncode==0 and 'Normal' in chrony.stdout,remoteprocs=rp,taint=0,fault_counts=faults,nv_and_product_programs_preserved=True,tools=tools,libcamera_packages=[n for n in packages.stdout.splitlines() if 'libcamera' in n or 'wireplumber' in n],uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]))
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
