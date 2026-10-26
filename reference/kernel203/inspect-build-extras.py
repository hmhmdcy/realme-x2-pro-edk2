from pathlib import Path
import configparser,json,subprocess

private=Path('/mnt/e/edk2-samurai-out/kernel203');base=Path('/home/cy122/pmos-samurai-rootfs01');native=base/'work/chroot_native'
report={}
config=configparser.ConfigParser();config.read(base/'pmbootstrap.cfg')
report['pmbootstrap_selected_config']={section:{name:value for name,value in config[section].items() if name in ['device','work','aports','arch','ui','channel','kernel','boot_size','system_size']} for section in config.sections()}
report['native_paths']={name:(native/name.lstrip('/')).is_file() for name in ['/bin/sh','sbin/apk','usr/bin/abuild','usr/bin/abuild-sign','usr/bin/openssl']}
report['key_file_count']=sum(1 for p in (base/'work/config_apk_keys').glob('*') if p.is_file())
report['abuild_config_entries']=sorted(p.name for p in (base/'work/config_abuild').iterdir())
for label,command in [('native-apk-version',['chroot',str(native),'/sbin/apk','--version']),('native-abuild-version',['chroot',str(native),'/usr/bin/abuild','-V']),('native-apk-tools',['chroot',str(native),'/sbin/apk','--help'])]:
 p=subprocess.run(command,capture_output=True,text=True,timeout=20);(private/(label+'-private.txt')).write_text(p.stdout+p.stderr);report[label]=dict(returncode=p.returncode,version=(p.stdout+p.stderr).splitlines()[:1])
matches=[]
for path in (base/'pmaports').glob('*/modemmanager/APKBUILD'):
 matches.append(str(path));(private/'modemmanager-original-APKBUILD').write_bytes(path.read_bytes())
report['modemmanager_apkbuilds']=matches
p=subprocess.run(['git','-C',str(base/'pmaports'),'rev-parse','HEAD'],capture_output=True,text=True,check=True);report['pmaports_commit']=p.stdout.strip()
(private/'build-extras-private.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
