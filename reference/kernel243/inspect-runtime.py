"""Fresh live state, diagnostics transport and RF-resource inventory. No SET."""
from pathlib import Path
import dbus,json,subprocess
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
def read(p):
 try:return Path(p).read_text(errors='replace')
 except OSError as e:return dict(error=e.errno)
def cmd(args):
 x=subprocess.run(args,capture_output=True,timeout=20);return dict(rc=x.returncode,stdout=x.stdout.decode(errors='replace'),stderr=x.stderr.decode(errors='replace'))
bus=dbus.SystemBus(private=True);owner=str(bus.get_name_owner('org.freedesktop.ModemManager1'))
objects=dbus.Interface(bus.get_object(owner,'/org/freedesktop/ModemManager1'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
interfaces=next(v for v in objects.values() if 'org.freedesktop.ModemManager1.Modem' in v);loc=interfaces['org.freedesktop.ModemManager1.Modem.Location'];m=interfaces['org.freedesktop.ModemManager1.Modem']
watch=json.loads((r/'gnss-assist/watch-state.json').read_text())
report=dict(stage=243,current236_boot=True,location_enabled=int(loc['Enabled']),location_signals=bool(loc['SignalsLocation']),gps_refresh=int(loc['GpsRefreshRate']),
 modem_state=int(m['State']),modem_power=int(m['PowerState']),assist_active=watch['active'],assist_data_worker_starts=watch['worker_starts'],taint=int(read('/proc/sys/kernel/tainted')),
 remoteprocs=[dict(name=read(p/'name').strip(),state=read(p/'state').strip()) for p in Path('/sys/class/remoteproc').glob('*')],
 diag_devices=[str(p) for p in Path('/dev').glob('*diag*')],readonly=True,no_flash_or_reboot=True)
private=dict(owner=owner,qrtr=cmd(['qrtr-lookup']),dmesg=cmd(['dmesg']),
 snapshots={p:read(p) for p in ['/sys/kernel/debug/regulator/regulator_summary','/sys/kernel/debug/pm_genpd/pm_genpd_summary','/sys/kernel/debug/clk/clk_summary','/sys/kernel/debug/gpio','/run/samurai-wifi/tftp.log','/run/samurai-wifi/rmtfs.log']},
 pinmux={str(p):read(p) for p in Path('/sys/kernel/debug/pinctrl').glob('*/pinmux-pins')},
 regulator_metadata={p.name:{n:read(p/n) for n in ['name','state','num_users','microvolts']}|dict(path=str(p.resolve()),of_node=str((p/'of_node').resolve())) for p in Path('/sys/class/regulator').glob('*')},
 modules=read('/proc/modules'),watch=watch,usb_speeds=[dict(path=str(p),speed=read(p)) for p in Path('/sys/class/udc').glob('*/current_speed')])
assert report['location_enabled']==0 and not report['assist_active'];bus.close();print(json.dumps(dict(report=report,private=private)))
