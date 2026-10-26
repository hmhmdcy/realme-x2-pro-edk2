from pathlib import Path
import hashlib,json,subprocess
import host

ref=Path(__file__).resolve().parent;dest=ref/'reboot-r2'
files=['collect-preflash.py','check-quiesce.py','disable-crtc.py','freeze-for-bootloader.sh',
 'linux-restart2-bootloader.py','quiesce-current183.sh','reboot-current.py','fastboot-reboot-current.py']
for name in files:
 data=(ref/name).read_text().replace('k189','k189r2')
 data=data.replace('/var/lib/samurai/k188-reboot-runtime/boot-id-private.txt','/var/lib/samurai/k189-reboot-runtime/boot-id-private.txt')
 if name=='fastboot-reboot-current.py':data=data.replace("host.PRIVATE.parent / 'kernel109/fastboot-identity.json'","host.PRIVATE.parents[1] / 'kernel109/fastboot-identity.json'")
 if name=='collect-preflash.py':
  marker='    assert hashlib.sha256((module_root / name).read_bytes()).hexdigest() == digest, name'
  assert data.count(marker)==1
  added="""    elif name == 'kernel/drivers/misc/fastrpc.ko':
        assert digest == '4515b1b22f212ce2ec482039343d9b72193ef2100e8b0b97227bdde2f37156aa'
        digest = '88553112839d0a23604171edb03004a15e94f7cc3b174ebb3b9f2e56d3cc2fcc'
        overrides += 1
"""
  data=data.replace(marker,added+marker).replace('overrides == 1','overrides == 2').replace('overrides=1','overrides=2')
 path=dest/name;assert not path.exists();path.write_text(data)
 subprocess.run(['sh','-n',str(path)] if name.endswith('.sh') else ['python3','-m','py_compile',str(path)],check=True)
host.ssh('test ! -e /var/lib/samurai/k189r2-reboot-tools && mkdir -m700 /var/lib/samurai/k189r2-reboot-tools')
for name in files:
 if name in ['reboot-current.py','fastboot-reboot-current.py']:continue
 path=dest/name;remote='/tmp/k189r2-'+name if name in ['check-quiesce.py','disable-crtc.py','freeze-for-bootloader.sh'] else '/var/lib/samurai/k189r2-reboot-tools/'+name
 host.upload(path,remote);host.ssh('sha256sum -c -',input=(hashlib.sha256(path.read_bytes()).hexdigest()+'  '+remote+'\n').encode())
p=host.ssh('python3 /var/lib/samurai/k189r2-reboot-tools/collect-preflash.py',timeout=55)
(host.PRIVATE/'r2-pre-reboot-capture-private.log').write_bytes(p.stdout+p.stderr)
print('Fresh boot identity and both candidate module file overrides verified; no reboot sent.')
