from pathlib import Path
import configparser,hashlib,json,os,subprocess
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k201-baseline/boot-id-private.txt').read_bytes()
out=root/'k201-geoclue-install';assert not out.exists();out.mkdir(mode=0o700)
configs=list(Path('/etc/geoclue').glob('*.conf'))+list(Path('/etc/geoclue/conf.d').glob('*.conf'))
sections={}
for p in configs:
 raw=p.read_bytes();(out/(p.name+'-private')).write_bytes(raw)
 config=configparser.ConfigParser(interpolation=None,strict=False);config.read_string(raw.decode())
 sections[p.name]={section:{key:value if key in ['enable','allowed','system','users','wifi','3g','cdma','gnss','modem-gps','accuracy-level','agent'] else '<private-value>' for key,value in config.items(section)} for section in config.sections()}
files={}
for p in [Path('/usr/libexec/geoclue'),Path('/usr/libexec/geoclue-2.0/demos/agent'),Path('/usr/libexec/geoclue-2.0/demos/where-am-i')]:
 if p.exists():files[str(p)]=dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size)
result=dict(stage=201,configuration=sections,installed_files=files)
for name,cmd in [('packages',['apk','info','-v','geoclue','geoclue-libs','geoclue-dev','modemmanager','libqmi']),('files',['apk','info','-L','geoclue']),('permissions',['ls','-l','/etc/dbus-1/system.d/org.freedesktop.GeoClue2.conf','/usr/share/dbus-1/system-services/org.freedesktop.GeoClue2.service'])]:
 p=subprocess.run(cmd,capture_output=True);(out/(name+'-private.txt')).write_bytes(p.stdout+p.stderr)
 if name=='packages':result[name]=p.stdout.decode().splitlines()
(out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
