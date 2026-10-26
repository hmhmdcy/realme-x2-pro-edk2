import host

native=r'''
from pathlib import Path
import dbus,json,subprocess
root=Path('/var/lib/samurai')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k207r2-runtime/boot-id-private.txt').read_bytes()
out=root/'k207r2-network-clock';out.mkdir(mode=0o700)
commands={'nm-device':['nmcli','-t','-f','GENERAL','device','show','wlan0'], 'nm-active':['nmcli','-t','connection','show','--active'], 'chrony-sources':['chronyc','-n','sources'], 'chrony-activity':['chronyc','activity'], 'routes':['ip','-j','route','show']}
data={}
for label,command in commands.items():
    p=subprocess.run(command,capture_output=True,text=True,timeout=15)
    (out/(label+'-private.txt')).write_text(p.stdout+p.stderr)
    data[label]=(p.returncode,p.stdout)
state=[line.split(':',1)[1] for line in data['nm-device'][1].splitlines() if line.startswith('GENERAL.STATE:')]
sources=[line[:2] for line in data['chrony-sources'][1].splitlines() if line.startswith(('^','=',' #','#'))]
routes=json.loads(data['routes'][1]) if data['routes'][0]==0 else []
bus=dbus.SystemBus(private=True)
nm=dbus.Interface(bus.get_object('org.freedesktop.NetworkManager','/org/freedesktop/NetworkManager'),'org.freedesktop.DBus.Properties')
report=dict(stage=207,boot_cycle=2,nm_wlan_state=state,networking_enabled=bool(nm.Get('org.freedesktop.NetworkManager','NetworkingEnabled')),wireless_enabled=bool(nm.Get('org.freedesktop.NetworkManager','WirelessEnabled')),nm_connectivity=int(nm.Get('org.freedesktop.NetworkManager','Connectivity')),chrony_source_states=sources,chrony_activity=data['chrony-activity'][1],default_routes=sum(route.get('dst')=='default' for route in routes),clock_synced=False,uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]))
bus.close()
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
'''
p=host.ssh('python3 -',input=native.encode(),timeout=90)
(host.PRIVATE/'network-clock-inspection-private.json').write_bytes(p.stdout)
print(p.stdout.decode())
