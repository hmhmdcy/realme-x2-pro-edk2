from pathlib import Path
import hashlib,json,re,tarfile
import host

ref=Path(__file__).resolve().parent;host.transport.PRIVATE=host.PRIVATE/'reboot-r2'
code='''from pathlib import Path
import os,json,subprocess,hashlib,shutil,dbus
os.umask(0o077)
out=Path('/var/lib/samurai/k189-final');assert not out.exists();out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k189r2-reboot-runtime/boot-id-private.txt').read_bytes()
log=subprocess.check_output(['dmesg'],text=True);(out/'dmesg-private.txt').write_text(log)
assert log.lstrip().startswith('[    0.')
remote={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')}
assert remote=={'adsp':'running','slpi':'running','modem':'running'}
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert Path('/sys/devices/platform/sensor-power/state').read_text().strip()=='vdd=1 vddio=1'
for name in ['samurai-ssc','iio-sensor-proxy']:
 assert subprocess.run(['rc-service',name,'status'],capture_output=True).returncode==0
for name,manifest in [('nv','/run/samurai-wifi/nv-source-hashes.txt'),('source','/var/lib/samurai/k111-sensor-sources-readonly/sources-before.sha256'),
 ('archive','/var/lib/samurai/k189-deploy/source-manifest-private.sha256'),('modules','/var/lib/samurai/k189r2-preflash/old132-module-tree.sha256')]:
 args=['sha256sum','-c',manifest]
 p=subprocess.run(args,cwd=Path('/usr/lib/modules')/os.uname().release if name=='modules' else '/',capture_output=True,check=True)
 (out/(name+'-check-private.txt')).write_bytes(p.stdout+p.stderr)
link=subprocess.check_output(['iw','dev','wlan0','link']);(out/'wifi-private.txt').write_bytes(link);assert b'freq: 5180' in link
assert subprocess.run(['pidof','phosh'],capture_output=True).stdout.strip()
bus=dbus.SystemBus(private=True)
props=dbus.Interface(bus.get_object('org.bluez','/org/bluez/hci0'),'org.freedesktop.DBus.Properties').GetAll('org.bluez.Adapter1')
objects=dbus.Interface(bus.get_object('org.bluez','/'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
assert not props['Powered'] and not props['Discovering'] and all(not v.get('org.bluez.Device1',{}).get('Connected',False) for v in objects.values())
bus.close()
patterns=dict(warning='WARNING:',oops='Oops:',gpu='gpu fault:',dpu='Frame done timeout',asoc='ASoC error',
 irq_read='Failed to read IRQ status',scm='Assign memory protection call failed',fastrpc='probe with driver qcom,fastrpc failed',
 slpi_fatal='fatal error received',bluetooth_reassembly='Frame reassembly failed')
faults={k:log.count(v) for k,v in patterns.items()}
assert not any(v for k,v in faults.items() if k!='bluetooth_reassembly') and faults['bluetooth_reassembly']==1
state=Path('/run/samurai-ssc/state.json').read_bytes();(out/'service-state-private.json').write_bytes(state)
def tree_hash(root):
 return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
ram=Path('/run/samurai-ssc/root');before=tree_hash(ram)
shutil.copytree(ram,out/'ram-root-private')
after=tree_hash(ram);copied=tree_hash(out/'ram-root-private')
assert before==after==copied
(out/'ram-tree-hashes-private.json').write_text(json.dumps(copied,indent=2))
for name in ['hexagonrpcd-private.log','transitions-private.log','accelerometer-readiness-private.log','light-readiness-private.log']:
 p=Path('/run/samurai-ssc')/name
 if p.exists():shutil.copyfile(p,out/name)
root=Path('/var/lib/samurai/k189-persistent-client/summary.json')
if root.exists():
 old=json.loads(root.read_text())
 if old.get('stage')==188:
  shutil.copyfile(root,root.with_name('summary-template-stage-r1-private.json'))
  old.update(stage=189,validation_template_stage=188);root.write_text(json.dumps(old,indent=2)+'\\n')
report=dict(stage=189,kernel_build=183,uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]),taint=0,
 remoteproc=remote,sensor_supplies_on=True,a11_independent_firmware_selected=Path('/sys/class/remoteproc/remoteproc0/firmware').read_text().strip().endswith('samurai-a11-r187/slpi.mdt'),
 persistent_ssc_and_proxy_running=True,default_module_overrides=2,source_archive_nv_and_module_tree_preserved=True,
 live_ram_snapshot_hash_consistent=True,phosh_running=True,wifi_frequency_mhz=5180,
 bluetooth_powered_off=True,bluetooth_connected=False,full_boot_fault_counts=faults,
 boot_has_known_bluetooth_failure=True,no_sensor_restart_or_driver_rebind_after_pm=True,goal_complete=False)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\\n');print(json.dumps(report))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=55);(host.PRIVATE/'final-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);(ref/'final-validation.json').write_text(json.dumps(report,indent=2)+'\n')
names='k189-final k189-deploy k189-module-deploy k189-tools k189-freezer-original k189-desktop-policy k189-persistent-client k189-ssc-pm k189-ssc-pm-r2 k189-ssc-pm-r3 k189r2-reboot-runtime k189r2-startup-inspection'
p=host.ssh('tar -C /var/lib/samurai -czf /tmp/k189-final-evidence-private.tar.gz '+names+' && sha256sum /tmp/k189-final-evidence-private.tar.gz',timeout=55)
digest=p.stdout.decode().split()[0];archive=host.PRIVATE/'final-evidence-private.tar.gz'
host.download('/tmp/k189-final-evidence-private.tar.gz',archive);assert hashlib.sha256(archive.read_bytes()).hexdigest()==digest
folder=host.PRIVATE/'final-evidence-private'
with tarfile.open(archive) as tar:tar.extractall(folder,filter='data')
runtime=json.loads((folder/'k189r2-reboot-runtime/summary.json').read_text());(ref/'candidate-reboot-runtime-validation.json').write_text(json.dumps(runtime,indent=2)+'\n')
three=[]
for suffix in ['', '-r2','-r3']:
 d=folder/('k189-ssc-pm'+suffix)
 item=json.loads((d/'validation.json').read_text());stats=json.loads((d/'trace-stats-private.json').read_text())
 assert len(stats)==8 and all(int(next(line.split(':',1)[1] for line in v.splitlines() if line.startswith('overrun:')))==0 for v in stats.values())
 three.append(item)
summary=dict(stage=189,cycles=3,all_sensor_resume_passed=all(i['suspend_and_sensor_resume_passed'] for i in three),
 suspend_success_delta=sum(i['suspend_stats_delta']['success'] for i in three),
 suspend_fail_delta=sum(i['suspend_stats_delta']['fail'] for i in three),
 rtc_irqs=sum(i['rtc_alarm_irq_delta'] for i in three),residency_seconds=[i['suspend_residency_seconds'] for i in three],
 callback_events=sum(i['callback_events'] for i in three),callback_errors=sum(i['callback_errors'] for i in three),
 all_eight_cpu_overruns_zero_verified=True,wifi_observation_delays_seconds=[i['wifi_association_observation_delay_seconds'] for i in three],
 wifi_recovery_within_window_all_cycles=all(i['wifi_frequency_mhz']==5180 for i in three),
 same_boot_only=True,cold_boot_or_long_term_sensor_reliability_verified=False,
 original188_suspend_failure_retained=True,general_signal_retry_and_slpi_restart_not_verified=True)
(ref/'three-cycle-suspend-validation.json').write_text(json.dumps(summary,indent=2)+'\n')
(ref/'evidence-export-validation.json').write_text(json.dumps(dict(sha256=digest,verified=True,private_only=True),indent=2)+'\n')
# Derive the startup UART phase from private logs without publishing surrounding identities.
log=(folder/'k189-final/dmesg-private.txt').read_text();lines=log.splitlines();matches=[]
for index,line in enumerate(lines):
 if 'Frame reassembly failed' in line:
  nearby=[l for l in lines[max(0,index-4):index+2] if 'qca setup uart RX' in l or 'Frame reassembly failed' in l]
  matches.extend(nearby)
(host.PRIVATE/'bluetooth-startup-context-private.txt').write_text('\n'.join(matches)+'\n')
print(json.dumps(report));print(json.dumps(summary))
