"""Verify the deployed coherent kernel, unchanged camera packages and post-test idle state."""
from pathlib import Path
import json
import host

ROOT=Path(__file__).resolve().parent
assert json.loads((ROOT/'four-camera-regression-validation.json').read_text())['passed']
assert json.loads((ROOT/'stats-pixel-validation.json').read_text())['all_phase_color_contracts_passed']
assert json.loads((ROOT/'statistics-pixel-validation.json').read_text())['passed']
assert json.loads((ROOT/'optical-pixel-validation.json').read_text())['exposure_response_and_return_passed']
assert json.loads((ROOT/'optical-statistics-validation.json').read_text())['all_packets_valid']
assert json.loads((ROOT/'statistics-r2-pixel-validation.json').read_text())['passed']
code=r'''
from pathlib import Path
import ast,dbus,hashlib,json,os,re,struct,subprocess
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k296-work/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#296 ')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
manifest=json.loads((r/'k278-package-transaction/new-manifest-private.json').read_text());checked=0
for package in manifest['packages']:
 for name,item in package['files'].items():
  p=Path('/')/name
  if item['kind']=='symlink':assert p.is_symlink() and os.readlink(p)==item['target']
  else:assert not p.is_symlink() and sha(p)==item['sha256'] and p.stat().st_mode&0o777==item['mode']
  checked+=1
assert checked==50
current=Path('/usr/lib/modules')/os.uname().release
inventory=json.loads((r/'k296-deployment/module-inventory-private.json').read_text())
assert len(inventory)==778 and inventory=={str(p.relative_to(current)):sha(p) for p in current.rglob('*.ko')}
middle=Path('/usr/lib/modules/7.3.0-rc6-rmx1931-samurai-k279candidate+')
middle_inventory=json.loads((r/'k288-deployment/module-inventory-private.json').read_text())
assert len(middle_inventory)==778 and middle_inventory=={str(p.relative_to(middle)):sha(p) for p in middle.rglob('*.ko')}
old=Path('/usr/lib/modules/7.3.0-rc6-rmx1931-samurai-k132+')
old_inventory=json.loads((r/'k278-package-transaction/module-inventory-before-private.json').read_text())
assert len(old_inventory)==776 and old_inventory=={str(p.relative_to(old)):sha(p) for p in old.rglob('*.ko')}
previous=Path('/usr/lib/modules/7.3.0-rc6-rmx1931-samurai-k290+')
previous_inventory=json.loads((r/'k290-deployment/module-inventory-private.json').read_text())
assert len(previous_inventory)==778 and previous_inventory=={str(p.relative_to(previous)):sha(p) for p in previous.rglob('*.ko')}
prior292=Path('/usr/lib/modules/7.3.0-rc6-rmx1931-samurai-k292+')
prior292_inventory=json.loads((r/'k292-deployment-r2/module-inventory-private.json').read_text())
assert len(prior292_inventory)==778 and prior292_inventory=={str(p.relative_to(prior292)):sha(p) for p in prior292.rglob('*.ko')}
prior293=Path('/usr/lib/modules/7.3.0-rc6-rmx1931-samurai-k293+')
prior293_inventory=json.loads((r/'k293-deployment/module-inventory-private.json').read_text())
assert len(prior293_inventory)==778 and prior293_inventory=={str(p.relative_to(prior293)):sha(p) for p in prior293.rglob('*.ko')}
prior294=Path('/usr/lib/modules/7.3.0-rc6-rmx1931-samurai-k294+')
prior294_inventory=json.loads((r/'k294-deployment/module-inventory-private.json').read_text())
assert len(prior294_inventory)==778 and prior294_inventory=={str(p.relative_to(prior294)):sha(p) for p in prior294.rglob('*.ko')}
prior295=Path('/usr/lib/modules/7.3.0-rc6-rmx1931-samurai-k295+')
prior295_inventory=json.loads((r/'k295-deployment/module-inventory-private.json').read_text())
assert len(prior295_inventory)==778 and prior295_inventory=={str(p.relative_to(prior295)):sha(p) for p in prior295.rglob('*.ko')}




unbooted=r/'k292-deployment/modules-r1-preserved'
unbooted_inventory=json.loads((r/'k292-deployment/module-inventory-private.json').read_text())
assert len(unbooted_inventory)==778 and unbooted_inventory=={str(p.relative_to(unbooted)):sha(p) for p in unbooted.rglob('*.ko')}

def note(path):
 b=Path(path).read_bytes();offset=struct.unpack_from('<Q',b,40)[0];size,count,index=struct.unpack_from('<HHH',b,58)
 sec=[struct.unpack_from('<IIQQQQIIQQ',b,offset+i*size) for i in range(count)];names=b[sec[index][4]:sec[index][4]+sec[index][5]]
 return next(b[s[4]:s[4]+s[5]] for s in sec if names[s[0]:].split(b'\0',1)[0]==b'.note.gnu.build-id')
modules={}
for name in ['qcom_camss','i2c_qcom_cci','s5k3m5','s5kgw1','imx319','imx471','lc898219xi','qcom_pm8008','qcom_pm8008_regulator','v4l2_cci']:
 p=Path(subprocess.check_output(['modinfo','-n',name],text=True).strip())
 assert Path('/sys/module',name,'notes/.note.gnu.build-id').read_bytes()==note(p)
 params=Path('/sys/module',name,'parameters')
 modules[name]=dict(sha256=sha(p),loaded=True,loaded_note_matches_disk=True,intree=subprocess.check_output(['modinfo','-F','intree',str(p)],text=True).strip(),
                   parameters={p.name:p.read_text().strip() for p in params.glob('*')} if params.exists() else {})
runtime={}
for driver in ['s5kgw1','s5k3m5','imx319','imx471','lc898219xi']:
 found=[p for p in Path('/sys/bus/i2c/drivers',driver).glob('*') if p.is_symlink() and re.fullmatch(r'\d+-[0-9a-f]{4}',p.name)]
 assert len(found)==1;runtime[driver]=dict(device=found[0].name,state=(found[0]/'power/runtime_status').read_text().strip())
for name in ['ac4a000.cci','ac4b000.cci','acb3000.camss']:
 runtime[name]=dict(state=Path('/sys/bus/platform/devices',name,'power/runtime_status').read_text().strip())
assert all(v['state']=='suspended' for v in runtime.values())
rails={}
for p in Path('/sys/class/regulator').glob('regulator.*'):
 n=(p/'name').read_text().strip()
 if n.startswith(('cam-main-','cam-front-','cam-rear-','cam-tele-')):rails[n]={k:(p/k).read_text().strip() for k in ['state','num_users']}
assert len(rails)==9 and all(v['state']=='disabled' and v['num_users']=='0' for v in rails.values())
lines=Path('/sys/kernel/debug/clk/clk_summary').read_text().splitlines()
clocks={n:int(next(l.split()[1] for l in lines if l.split() and l.split()[0]==n)) for n in ['cam_cc_mclk0_clk','cam_cc_mclk1_clk','cam_cc_mclk2_clk','cam_cc_mclk3_clk','cam_cc_cci_0_clk','cam_cc_cci_1_clk']}
assert not any(clocks.values())
supply=Path('/sys/bus/platform/devices/ac4a000.cci/of_node/vddio-supply').read_bytes()
node=next(p.parent for p in Path('/sys/firmware/devicetree/base').rglob('phandle') if p.read_bytes()==supply)
io=next(p for p in Path('/sys/class/regulator').glob('regulator.*') if (p/'of_node').exists() and (p/'of_node').resolve()==node)
io_state={k:(io/k).read_text().strip() for k in ['state','num_users']};assert io_state==dict(state='disabled',num_users='0')
processes=[]
for name in ['phoc','phosh','pipewire','wireplumber']:
 pids=subprocess.check_output(['pgrep','-x',name],text=True).split();assert len(pids)==1
 pid=pids[0];p=Path('/proc',pid);f=(p/'stat').read_text().rsplit(')',1)[1].split();assert f[0]!='Z'
 processes.append(dict(comm=name,pid=int(pid),start_ticks=f[19]))
 versions={p['name']:p['version'] for p in manifest['packages']}
(r/'k296-services-verified-private.json').write_text(json.dumps(dict(processes=processes),indent=2)+'\n')
kernel=subprocess.check_output(['dmesg']);faults={k:kernel.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu_fault=b'gpu fault:',dsp_fatal=b'fatal error received').items()}
assert not any(faults.values()) and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
cci_errors=[l for l in kernel.decode(errors='replace').splitlines() if 'i2c-qcom-cci' in l and any(s in l.lower() for s in ['timeout','failed','nack'])];assert not cci_errors
assert not list(Path('/sys/fs/pstore').glob('*'))

ssc=json.loads(Path('/run/samurai-ssc/state.json').read_text())
assert ssc['attempted']
ssc_ok=bool(ssc['started'])
if ssc_ok:
 assert subprocess.run(['rc-service','iio-sensor-proxy','status'],capture_output=True).returncode==0
 bus=dbus.SystemBus(private=True);prop=dbus.Interface(bus.get_object('net.hadess.SensorProxy','/net/hadess/SensorProxy'),'org.freedesktop.DBus.Properties')
 proxy={k:bool(prop.Get('net.hadess.SensorProxy',k)) for k in ['HasAccelerometer','HasAmbientLight','HasProximity']};bus.close()
 assert all(proxy.values())
else:
 assert ssc['stopped'] and ssc['readiness_failure']['daemon_returncode']==4
 assert subprocess.run(['rc-service','iio-sensor-proxy','status'],capture_output=True).returncode!=0
 proxy={k:False for k in ['HasAccelerometer','HasAmbientLight','HasProximity']}
 restore=json.loads((r/'k296-desktop-restore-r1/summary.json').read_text());assert restore['desktop_started'] and restore['dependency_config_unchanged'] and restore['failed_slpi_start_not_retried']
assert sha('/etc/conf.d/greetd')=='290ac45da696238afa1341d65d82bd28898fef749cdc77ff2b2bc19647211323'
dsps={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('*')}
assert all(dsps[n]=='running' for n in ['modem','adsp']) and dsps['slpi']==('running' if ssc_ok else 'offline')

db=Path('/lib/apk/db/installed').read_bytes();packages=sum(1 for p in db.split(b'\n\n') if any(l.startswith(b'P:') for l in p.splitlines()));assert packages==961
bt=dict(hci_present=Path('/sys/class/bluetooth/hci0').exists(),hci_uart_loaded=Path('/sys/module/hci_uart').exists())
report=dict(stage=296,kernel_build=296,release=os.uname().release,module_count=778,all778_modules_verified=True,old776_modules_preserved=True,old288_778_modules_preserved=True,
 current50_payloads_verified=50,package_count=packages,package_versions=versions,modules=modules,runtime=runtime,rails=rails,clocks=clocks,
 shared_io_supply=io_state,processes=processes,faults=faults,taint=0,pstore_files=0,cci_errors=cci_errors,
 sensor_proxy=proxy,remoteprocs=dsps,bluetooth=bt,wlan_state=Path('/sys/class/net/wlan0/operstate').read_text().strip(),
 whole_system_healthy=False,checked_runtime_healthy=ssc_ok,ssc_default_start_failed=not ssc_ok,ssc_failure_exit=None if ssc_ok else 4,desktop_recovered_with_temporary_nodeps=not ssc_ok,automatic_rotation_available=ssc_ok,
 camera_tests_and_resource_health_passed=True,
 experimental_tpg_nv12_transport_verified=True,hardware_isp_full_color_and_physical_quality_not_yet_complete=True,hardware_isp_userspace_not_integrated=True,
 four_camera_raw_cpu_isp_regression_passed=True,physical_rotation_and_new_boot_auto_af_not_retested=True,standard_tpg_no_mmio=True,two_physical_csi_sensor_patterns_verified=True,physical_scene_quality_unverified=True,physical_scene_exposure_response_verified=True,standard_wb_params_verified=True,standard_bhist_validation_pending=False,standard_bhist_initialization_verified=True,statistics_ready_for_automatic_exposure=False,standard_bhist_pattern_steady_frames_verified=True,first_statistics_packet_invalid=False,old295_778_modules_preserved=True,old294_778_modules_preserved=True,old293_778_modules_preserved=True,old290_778_modules_preserved=True,old292_778_modules_preserved=True,unbooted_r1_778_modules_preserved=True)
(r/'k296-tools/final-health-private.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=40)
(host.PRIVATE/'final-health-new-boot-private.json').write_bytes(q.stdout)
report=json.loads(q.stdout);(ROOT/'final-health-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['modules','rails']},indent=2))
