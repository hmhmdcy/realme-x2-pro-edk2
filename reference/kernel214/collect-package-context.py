from pathlib import Path
import host,json
here=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import json,os,subprocess
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k214-baseline/boot-id-private.txt').read_bytes()
processes=[]
for p in Path('/proc').iterdir():
    if not p.name.isdigit():continue
    try:
        comm=(p/'comm').read_text().strip()
        if comm not in ['wireplumber','pipewire','phosh','phoc','gnome-session-b']:continue
        uid=int((p/'status').read_text().split('Uid:',1)[1].split()[0])
        if uid!=10000:continue
        parent=int((p/'status').read_text().split('PPid:',1)[1].split()[0]);parent_comm=Path('/proc',str(parent),'comm').read_text().strip()
        libraries=sorted({line.split()[-1] for line in (p/'maps').read_text().splitlines() if '/usr/lib/libcamera' in line})
        env=dict(entry.split(b'=',1) for entry in (p/'environ').read_bytes().split(b'\0') if b'=' in entry)
        selected={key.decode():value.decode() for key,value in env.items() if key.decode() in ['XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS','XDG_CONFIG_HOME','XDG_DATA_HOME','WAYLAND_DISPLAY','DISPLAY','HOME','USER','LANG']}
        processes.append(dict(pid=int(p.name),comm=comm,parent=parent,parent_comm=parent_comm,exe=os.readlink(p/'exe'),argv=[x.decode() for x in (p/'cmdline').read_bytes().split(b'\0') if x],environment=selected,camera_libraries=libraries))
    except OSError:pass
files={name:(root/'k214-baseline'/name).read_text() for name in ['original-files-manifest-private.json']}
files['world-private.txt']=Path('/etc/apk/world').read_text()
init=Path('/etc/init.d/wireplumber');files['wireplumber-init-private.txt']=init.read_text() if init.is_file() else ''
print(json.dumps(dict(processes=processes,files=files,apk_database_bytes=Path('/lib/apk/db/installed').stat().st_size)))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=40);record=json.loads(p.stdout);(host.PRIVATE/'phone-package-context-private.json').write_bytes(p.stdout)
for name,text in record['files'].items():(host.PRIVATE/('phone-'+name)).write_text(text)
print(json.dumps(dict(stage=214,desktop_processes=[dict(comm=p['comm'],parent_comm=p['parent_comm'],camera_library_loaded=bool(p['camera_libraries'])) for p in record['processes']],installed_database_bytes=record['apk_database_bytes'],original_file_records_retrieved=True,phone_configuration_not_changed=True)))
