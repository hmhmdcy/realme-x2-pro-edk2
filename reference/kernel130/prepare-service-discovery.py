from pathlib import Path
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel130'
old=(ref/'test-bluez-discovery-r2.py').read_text()
new=old.replace("k130-bluez-discovery-r2')","k130-bluez-service-discovery')")
new=new.replace("assert not subprocess.run(['pgrep','-x','bluetoothd'],stdout=subprocess.DEVNULL).returncode==0", "assert subprocess.run(['pgrep','-x','bluetoothd'],stdout=subprocess.DEVNULL).returncode==0")
new=new.replace("assert not bus.name_has_owner('org.bluez')", "assert bus.name_has_owner('org.bluez')")
start=new.index("    daemon=subprocess.Popen(")
end=new.index("    objman=",start)
new=new[:start]+'''    dbus_api=dbus.Interface(bus.get_object('org.freedesktop.DBus','/org/freedesktop/DBus'),'org.freedesktop.DBus')
    owner_pid=int(dbus_api.GetConnectionUnixProcessID('org.bluez',timeout=8))
    assert owner_pid in [int(x) for x in subprocess.check_output(['pgrep','-x','bluetoothd'],text=True).split()]
    service_status=subprocess.check_output(['rc-service','bluetooth','status'],text=True)
    assert 'status: started' in service_status
    (root/'service-status-before.txt').write_text(service_status)
'''+new[end:]
new=new.replace("original_daemon_stopped=True,daemon_stopped=True", "original_daemon_stopped=False,daemon_stopped=False,daemon_service_running=True")
anchor="    capture('dmesg-after.txt',['dmesg'])"
new=new.replace(anchor, "    capture('service-status-after.txt',['rc-service','bluetooth','status'])\n"+anchor)
p=ref/'test-bluez-service-discovery.py';assert not p.exists();p.write_text(new)
print('K130_SERVICE_DISCOVERY_ONE_SHOT_PREPARED')
