from pathlib import Path
import host,json
here=Path(__file__).resolve().parent
for name in ['system-dark-raw','system-white-raw','system-white-rgb','system-dark-rgb']:
    result=json.loads((here/(name+'-validation.json')).read_text());assert result['program_exit']==0 and result['taint']==0 and not any(result['fault_delta'].values()) and result['camera_devices_suspended']
clients=json.loads((here/'default-clients-validation.json').read_text());assert all(v['exit']==0 and v['frames']==6 for v in clients['clients'].values())
code=r'''
from pathlib import Path
import dbus,hashlib,json,os,re,stat,subprocess
os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k214-final-health';out.mkdir(mode=0o700);base=root/'k214-baseline'
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(base/'boot-id-private.txt').read_bytes()
assert Path('/sys/firmware/devicetree/base/model').read_bytes()==b'Realme X2 Pro (RMX1931CN)\0' and os.uname().version.startswith('#183 ')
state=json.loads((root/'k214-package-transaction/transaction-state-private.json').read_text());assert state['state']=='verified'
policy=json.loads((root/'k214-package-transaction/policy-reload-state-private.json').read_text());assert policy['state']=='verified'
manifest=json.loads((root/'k214-package-candidates/forward-manifest.json').read_text())
paths={name for package in manifest['packages'] for name in package['files']}
original=json.loads((base/'products-before-private.json').read_text())
for name,digest in original.items():
    if name.lstrip('/') not in paths:assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest
checked=0
for package in manifest['packages']:
    for name,item in package['files'].items():
        p=Path('/')/name
        if item['kind']=='symlink':assert p.is_symlink() and os.readlink(p)==item['target']
        else:assert p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256'] and stat.S_IMODE(p.stat().st_mode)==item['mode']
        checked+=1
devices={'sensor':Path('/sys/bus/i2c/devices/7-0010'),'camss':Path('/sys/bus/platform/devices/acb3000.camss'),'cci':Path('/sys/bus/platform/devices/ac4b000.cci')}
assert (devices['sensor']/'driver').resolve().name=='imx471'
pm={name:(p/'power/runtime_status').read_text().strip() for name,p in devices.items()};assert all(value=='suspended' for value in pm.values())
rails={}
for p in Path('/sys/class/regulator').glob('regulator.*'):
    name=(p/'name').read_text().strip()
    if name in ['cam-front-vdig','cam-front-vana']:rails[name]={n:(p/n).read_text().strip() for n in ['state','num_users','microvolts']}
assert len(rails)==2 and all(x['state']=='disabled' and x['num_users']=='0' for x in rails.values())
clocks=Path('/sys/kernel/debug/clk/clk_summary').read_text();mclk=next(l.split() for l in clocks.splitlines() if re.search(r'\bcam_cc_mclk2_clk\s',l));assert int(mclk[1])==0
pd=Path('/sys/kernel/debug/pm_genpd/pm_genpd_summary').read_text();assert re.search(r'genpd:3:acb3000.camss\s+suspended\s+0\s',pd)
(out/'clock-private.txt').write_text(clocks);(out/'genpd-private.txt').write_text(pd)
for name in ['imx471 7-0010','msm_csid0']:
    nodes=[p for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().strip()==name];assert len(nodes)==1
    text=subprocess.check_output(['v4l2-ctl','-d','/dev/'+nodes[0].name,'--get-ctrl=test_pattern'],text=True,timeout=10);assert re.search(r'^test_pattern:\s*0(?:\s|\(|$)',text)
bus=dbus.SystemBus(private=True);props=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1/Modem/0'),'org.freedesktop.DBus.Properties')
loc=props.GetAll('org.freedesktop.ModemManager1.Modem.Location');assert int(loc['Enabled'])==0 and not loc['SignalsLocation'] and int(loc['GpsRefreshRate'])==30
assert not bus.name_has_owner('org.freedesktop.GeoClue2')
objects=dbus.Interface(bus.get_object('org.bluez','/'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects();adapters=[v['org.bluez.Adapter1'] for v in objects.values() if 'org.bluez.Adapter1' in v]
assert len(adapters)==1 and not adapters[0]['Powered'] and not adapters[0]['Discovering'] and not any(v.get('org.bluez.Device1',{}).get('Connected',False) for v in objects.values());bus.close()
watch=json.loads((root/'gnss-assist/watch-state.json').read_text());(out/'watch-private.json').write_text(json.dumps(watch,indent=2)+'\n');assert watch['running'] and not watch['active'] and watch['worker_starts']==watch['worker_completions']
chrony=subprocess.run(['chronyc','tracking'],capture_output=True,text=True,timeout=10);(out/'chrony-private.txt').write_text(chrony.stdout+chrony.stderr)
log=subprocess.check_output(['dmesg']);(out/'dmesg-private.txt').write_bytes(log)
faults={k:log.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()};assert not any(faults.values())
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
rp={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')};assert len(rp)==3 and all(v=='running' for v in rp.values())
for args,name in [(['sha256sum','-c','/run/samurai-wifi/nv-source-hashes.txt'],'nv'),(['sha256sum','-c',str(root/'k212-before-reboot/userspace-check.sha256')],'uncamera-product')]:
    with (out/(name+'-check-private.txt')).open('wb') as log:subprocess.run(args,check=True,stdout=log,stderr=subprocess.STDOUT,timeout=30)
records={}
for block in Path('/lib/apk/db/installed').read_text().split('\n\n'):
    fields={line[:1]:line[2:] for line in block.splitlines() if len(line)>1 and line[1]==':' and line[0] in 'PV'}
    if 'P' in fields:records[fields['P']]=fields['V']
assert len(records)==944 and all(records[p['name']]==p['version'] for p in manifest['packages'])
wp=Path('/proc',str(policy['new_pid']));assert (wp/'comm').read_text().strip()=='wireplumber' and 'libcamera.so' in (wp/'maps').read_text()
assert '(deleted)' not in '\n'.join(line for line in (wp/'maps').read_text().splitlines() if '/usr/lib/libcamera' in line)
report=dict(stage=214,same_boot_after_package_upgrade=True,kernel183_and_boot211_unchanged=True,camera_packages_upgraded_and_native_transaction_verified=True,installed_package_count=944,camera_payload_records_verified=checked,static_front_still_bound=True,camera_devices_pm=pm,front_rails_disabled_zero_users=True,mclk_off_and_own_mmcx_vote_zero=True,all_test_patterns_disabled=True,new_wireplumber_camera_libraries_loaded=True,gps_enabled=0,signals_location=False,gps_refresh_rate=30,bt_powered=False,bt_connections=0,gnss_watcher_idle=True,gnss_time_prepared=watch['time_prepared'],gnss_time_preparation_attempts=watch['time_preparation_starts'],chrony_normal=chrony.returncode==0 and 'Normal' in chrony.stdout,remoteprocs=rp,taint=0,fault_counts=faults,nv_and_non_camera_product_programs_preserved=True,no_flash_or_reboot=True,uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]))
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=100);(host.PRIVATE/'final-health-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);(here/'final-health-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
