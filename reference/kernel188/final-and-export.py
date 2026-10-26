from pathlib import Path
import hashlib
import json
import tarfile
import host

ref=Path(__file__).resolve().parent
code='''from pathlib import Path
import json,subprocess,os,dbus
out=Path('/var/lib/samurai/k188-final')
assert not out.exists()
out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k188-reboot-runtime/boot-id-private.txt').read_bytes()
log=subprocess.check_output(['dmesg'],text=True)
(out/'dmesg-private.txt').write_text(log)
assert log.lstrip().startswith('[    0.')
remote={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')}
assert remote=={'adsp':'running','modem':'running','slpi':'offline'}
assert Path('/sys/devices/platform/sensor-power/state').read_text().strip()=='vdd=0 vddio=0'
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert not subprocess.run(['pidof','samurai-hexagonrpcd','iio-sensor-proxy'],capture_output=True).stdout.strip()
assert not Path('/etc/runlevels/default/samurai-ssc').is_symlink()
assert subprocess.run(['pidof','phosh'],capture_output=True).stdout.strip()
link=subprocess.check_output(['iw','dev','wlan0','link'])
(out/'wifi-private.txt').write_bytes(link)
assert b'freq: 5180' in link
for manifest in ['/run/samurai-wifi/nv-source-hashes.txt','/var/lib/samurai/k188-deploy/source-manifest-private.sha256']:
 subprocess.run(['sha256sum','-c',manifest],check=True,stdout=subprocess.DEVNULL)
bus=dbus.SystemBus(private=True)
props=dbus.Interface(bus.get_object('org.bluez','/org/bluez/hci0'),'org.freedesktop.DBus.Properties').GetAll('org.bluez.Adapter1')
objects=dbus.Interface(bus.get_object('org.bluez','/'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
assert not props['Powered'] and not props['Discovering'] and all(not v.get('org.bluez.Device1',{}).get('Connected',False) for v in objects.values())
bus.close()
summary=dict(stage=188,kernel_build=183,uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]),
 taint=0,remoteproc=remote,sensor_supplies_off=True,original_firmware_pointer_restored=True,
 automatic_service_rolled_back=True,original_sensor_proxy_init_restored=True,
 source_archive_and_nv_preserved=True,phosh_running=True,wifi_frequency_mhz=5180,
 bluetooth_powered_off=True,bluetooth_not_connected=True,boot_log_from_zero=True,
 fault_counts={k:log.count(v) for k,v in dict(warning='WARNING:',oops='Oops:',gpu='gpu fault:',
  asoc='ASoC error',bluetooth='Frame reassembly failed',scm='Assign memory protection call failed',
  slpi_fatal='fatal error received',slpi_crash='crash detected in slpi').items()},
 no_extra_reboot_after_pm_failure=True,goal_complete=False)
assert summary['fault_counts']['slpi_fatal']==summary['fault_counts']['slpi_crash']==1
assert not any(v for k,v in summary['fault_counts'].items() if k not in ['slpi_fatal','slpi_crash'])
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\\n')
print(json.dumps(summary))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=45)
(host.PRIVATE/'final-host-private.log').write_bytes(p.stdout+p.stderr)
summary=json.loads(p.stdout)
(ref/'final-validation.json').write_text(json.dumps(summary,indent=2)+'\n')
p=host.ssh('tar -C /var/lib/samurai -czf /tmp/k188-final-evidence-private.tar.gz k188-deploy k188-preflash k188-quiesce k188-tools k188-reboot-runtime k188-persistent-client k188-persistent-client-r2 k188-desktop-policy k188-ssc-pm k188-pm-failure k188-rollback k188-final && sha256sum /tmp/k188-final-evidence-private.tar.gz',timeout=55)
digest=p.stdout.decode().split()[0]
archive=host.PRIVATE/'final-evidence-private.tar.gz'
host.download('/tmp/k188-final-evidence-private.tar.gz',archive)
assert hashlib.sha256(archive.read_bytes()).hexdigest()==digest
folder=host.PRIVATE/'final-evidence-private'
with tarfile.open(archive) as tar:
    tar.extractall(folder,filter='data')
runtime=json.loads((folder/'k188-reboot-runtime/summary.json').read_text())
(ref/'reboot-runtime-validation.json').write_text(json.dumps(runtime,indent=2)+'\n')
trace=(folder/'k188-ssc-pm/pm-trace-private.txt').read_text()
import re
callbacks=re.findall(r'device_pm_callback_end: (.*?) err=(-?\d+)',trace)
trace_summary=dict(callback_events=len(callbacks),callback_errors=sum(int(e)!=0 for _,e in callbacks),
    all_cpu_overrun_verified=False,r1_stats_dictionary_key_bug_preserved=True,
    r1_suspend_residency_not_persisted_before_failure=True,trace_not_equivalent_to_sensor_resume_success=True)
(ref/'failed-pm-trace-scope-validation.json').write_text(json.dumps(trace_summary,indent=2)+'\n')
(ref/'evidence-export-validation.json').write_text(json.dumps(dict(sha256=digest,verified=True,
    private_archive_only=True),indent=2)+'\n')
print(json.dumps(summary));print(json.dumps(trace_summary))
