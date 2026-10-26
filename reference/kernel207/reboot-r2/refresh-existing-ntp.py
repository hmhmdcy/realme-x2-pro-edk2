"""Refresh only existing chrony sources after Wi-Fi is online."""
import host

native=r'''
from pathlib import Path
import dbus,json,subprocess
root=Path('/var/lib/samurai')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k207r2-runtime/boot-id-private.txt').read_bytes()
out=root/'k207r2-ntp-refresh';assert not out.exists();out.mkdir(mode=0o700)
bus=dbus.SystemBus(private=True)
props=dbus.Interface(bus.get_object('org.freedesktop.NetworkManager','/org/freedesktop/NetworkManager'),'org.freedesktop.DBus.Properties')
assert int(props.Get('org.freedesktop.NetworkManager','Connectivity'))==4
bus.close()
results={}
for label,args in [('refresh',['refresh']),('online',['online']),('burst',['burst','4/4'])]:
    p=subprocess.run(['chronyc',*args],capture_output=True,text=True,timeout=15)
    (out/(label+'-private.txt')).write_text(p.stdout+p.stderr)
    assert p.returncode==0
    results[label]=p.stdout.strip()
print(json.dumps(dict(stage=207,existing_sources_only=True,no_ntp_config_change=True,no_manual_clock_set=True,requests=results)))
'''
p=host.ssh('python3 -',input=native.encode(),timeout=60)
(host.PRIVATE/'ntp-refresh-private.json').write_bytes(p.stdout)
print(p.stdout.decode())
