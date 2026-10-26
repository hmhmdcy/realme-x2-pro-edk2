from pathlib import Path
import ast,hashlib,json

here=Path(__file__).resolve().parent;out=here/'reboot-r2';assert not out.exists();out.mkdir()
private=Path('/mnt/e/edk2-samurai-out/kernel202/reboot-r2');assert not private.exists();private.mkdir(mode=0o700)
digest=hashlib.sha256((here/'samurai-gnss-assist.py').read_bytes()).hexdigest()
for name in ['collect-pre-reboot.py','stop-gnss-idle.py','quiesce-current183.sh','disable-crtc.py','check-quiesce.py','freeze-for-bootloader.sh','linux-restart2-bootloader.py','deploy-and-quiesce.py','reboot-current.py','fastboot-reboot-current.py','refresh-usb-endpoint.ps1','collect-newboot.py','connect-newboot.py']:
    source=(here/name).read_text().replace('k202','k202r2').replace('kernel202','kernel202/reboot-r2')
    if name=='collect-pre-reboot.py':
        source=source.replace('k201-baseline','k202-runtime').replace('cf3d92a46e619ceba30342fb2c063fb39ba9de5ddd2043e5dc0a5f59f39bef41',digest)
        source=source.replace("int(m['PowerState'])==3", "int(m['PowerState'])==1")
        source=source.replace("watch['source_sha256']==expected", "watch['time_prepared'] and watch['time_preparation_starts']==watch['time_preparation_completions']==1\nassert watch['source_sha256']==expected")
        source=source.replace('same_boot200=True','same_boot202_first_cycle=True')
    if name=='stop-gnss-idle.py':
        source=source.replace("pid = int(", "assert state['time_prepared'] and state['time_preparation_starts']==state['time_preparation_completions']==1\npid = int(")
    if name=='fastboot-reboot-current.py':source=source.replace('host.PRIVATE.parent /', 'host.PRIVATE.parents[1] /')
    if name=='collect-newboot.py':
        source=source.replace('import dbus, hashlib, json, os, struct, subprocess', 'import dbus, hashlib, json, os, struct, subprocess, time')
        source=source.replace("assert watch['running'] and not watch['active']", "deadline=time.monotonic()+75\nwhile not (watch['running'] and watch.get('time_prepared')) and time.monotonic()<deadline:\n    time.sleep(2)\n    watch=json.loads((root/'gnss-assist/watch-state.json').read_text())\n(out/'watch-ready-private.json').write_text(json.dumps(watch,indent=2)+'\\n')\nassert watch['time_prepared'] and watch['time_preparation_starts']==watch['time_preparation_completions']==1\nassert watch['running'] and not watch['active']")
        source=source.replace('manual_time_or_assistance_injection=False,', "manual_time_or_assistance_injection=False, idle_utc_preparation_automatic=True, idle_utc_preparation=watch['time_preparation_last_result'],")
    if name=='connect-newboot.py':source=source.replace("parent.parent/'kernel188/host.py'", "parent.parent.parent/'kernel188/host.py'").replace("here.parent/'kernel188/host.py'", "here.parent.parent/'kernel188/host.py'").replace('timeout=100','timeout=160')
    if name.endswith('.py'):ast.parse(source)
    (out/name).write_text(source)
(out/'host.py').write_text("from pathlib import Path\nimport importlib.util\nspec=importlib.util.spec_from_file_location('current202',Path(__file__).resolve().parent.parent/'host.py');transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport)\nssh,upload,download=transport.ssh,transport.upload,transport.download\nPRIVATE=Path('/mnt/e/edk2-samurai-out/kernel202/reboot-r2');PRIVATE.mkdir(mode=0o700,exist_ok=True)\n")
(out/'run-native.py').write_bytes((here/'run-native.py').read_bytes())
print('Prepared second reboot guards for the modified helper; no device transition sent.')
