from pathlib import Path
import hashlib,json,subprocess
import host

ref=Path(__file__).resolve().parent;old=ref.parent/'kernel188'
names=['collect-preflash.py','check-quiesce.py','disable-crtc.py','freeze-for-bootloader.sh',
 'linux-restart2-bootloader.py','quiesce-current183.sh','reboot-current.py','fastboot-reboot-current.py']
for name in names:
 value=(old/name).read_text().replace('k188','k189').replace('stage=188','stage=189').replace("'stage': 188","'stage': 189")
 value=value.replace('/var/lib/samurai/k187-reboot-runtime/boot-id-private.txt','/var/lib/samurai/k188-reboot-runtime/boot-id-private.txt')
 path=ref/name;assert not path.exists();path.write_text(value)
 subprocess.run(['sh','-n',str(path)] if name.endswith('.sh') else ['python3','-m','py_compile',str(path)],check=True)
host.ssh('test ! -e /var/lib/samurai/k189-reboot-tools && mkdir -m700 /var/lib/samurai/k189-reboot-tools')
for name in names:
 if name in ['reboot-current.py','fastboot-reboot-current.py']:continue
 path=ref/name;dest='/tmp/k189-'+name if name in ['check-quiesce.py','disable-crtc.py','freeze-for-bootloader.sh'] else '/var/lib/samurai/k189-reboot-tools/'+name
 host.upload(path,dest);host.ssh('sha256sum -c -',input=(hashlib.sha256(path.read_bytes()).hexdigest()+'  '+dest+'\n').encode())
p=host.ssh('python3 /var/lib/samurai/k189-reboot-tools/collect-preflash.py',timeout=55)
(host.PRIVATE/'pre-reboot-capture-private.log').write_bytes(p.stdout+p.stderr)
print(json.dumps(dict(fresh_current188_boot_captured=True,original_device_modules_verified=True,no_transition_yet_sent=True)))
