from pathlib import Path
import dbus,json,subprocess
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k210-runtime/boot-id-private.txt').read_bytes()
out=root/'k210-early-inspection';out.mkdir(mode=0o700)
log=subprocess.check_output(['dmesg']);(out/'dmesg-private.txt').write_bytes(log)
services=subprocess.run(['rc-status','-a'],capture_output=True);(out/'rc-status-private.txt').write_bytes(services.stdout+services.stderr)
bootstrap=Path('/var/log/samurai-native-bootstrap.log')
if bootstrap.exists():(out/'bootstrap-private.log').write_bytes(bootstrap.read_bytes())
dt=Path('/sys/firmware/devicetree/base');matches=[]
for p in Path('/sys/bus/i2c/devices').iterdir():
    if (p/'of_node').exists() and (p/'of_node').resolve().name in ['camera@10','pmic@4']:
        matches.append(dict(node=str((p/'of_node').resolve()).removeprefix(str(dt)),device=p.name,driver=(p/'driver').resolve().name if (p/'driver').exists() else None))
media={}
for p in Path('/dev').glob('media*'):
    r=subprocess.run(['media-ctl','-d',str(p),'-p'],capture_output=True);(out/(p.name+'-private.txt')).write_bytes(r.stdout+r.stderr);media[p.name]=dict(entities=r.stdout.count(b'entity '),imx471=b'imx471' in r.stdout)
bus=dbus.SystemBus(private=True);owners={n:bus.name_has_owner(n) for n in ['org.bluez','org.freedesktop.ModemManager1','org.freedesktop.GeoClue2']};bus.close()
rp={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')}
report=dict(stage=210,uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]),taint=int(Path('/proc/sys/kernel/tainted').read_text()),fault_counts={k:log.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()},camera_devices=matches,media=media,dbus_owners=owners,remoteprocs=rp,bootstrap_log_present=bootstrap.exists(),bootstrap_log_tail=(bootstrap.read_text(errors='replace').splitlines()[-1] if bootstrap.exists() else None))
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
