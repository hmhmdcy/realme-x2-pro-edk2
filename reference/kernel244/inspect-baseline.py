from pathlib import Path
import dbus,json,subprocess
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
bus=dbus.SystemBus(private=True);owner=str(bus.get_name_owner('org.freedesktop.ModemManager1'));objects=dbus.Interface(bus.get_object(owner,'/org/freedesktop/ModemManager1'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects();path,v=next((str(p),v) for p,v in objects.items() if 'org.freedesktop.ModemManager1.Modem' in v)
modem=v['org.freedesktop.ModemManager1.Modem'];loc=v['org.freedesktop.ModemManager1.Modem.Location'];assert int(loc['Enabled'])==0 and not json.loads((r/'gnss-assist/watch-state.json').read_text())['active']
x=subprocess.run(['qmicli','-p','-d','qrtr://0','--dms-get-operating-mode'],capture_output=True,timeout=20)
qrtr=subprocess.check_output(['qrtr-lookup']).decode();rpmsg=[dict(name=(p/'name').read_text().strip() if (p/'name').exists() else p.name,driver=(p/'driver').is_symlink()) for p in Path('/sys/bus/rpmsg/devices').glob('*')]
report=dict(stage=244,same236_boot=True,mm_power=int(modem['PowerState']),mm_state=int(modem['State']),dms_get_rc=x.returncode,mode_lines=[line.strip() for line in x.stdout.decode().splitlines() if 'Mode:' in line],
 diag_services=[line.split()[:5] for line in qrtr.splitlines() if line.split() and line.split()[0]=='4097'],rpmsg_diag_channels=[v for v in rpmsg if 'diag' in v['name'].lower()],taint=int(Path('/proc/sys/kernel/tainted').read_text()))
bus.close();print(json.dumps({'report':report,'private':{'qmicli_stdout':x.stdout.decode(),'qmicli_stderr':x.stderr.decode(),'qrtr':qrtr,'rpmsg':rpmsg,'mm_owner':owner,'modem_path':path,'dmesg':subprocess.check_output(['dmesg']).decode()}}))
