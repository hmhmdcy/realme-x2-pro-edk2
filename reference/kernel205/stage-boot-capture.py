from pathlib import Path
import hashlib,json,subprocess
import host

here=Path(__file__).resolve().parent;source=(host.PRIVATE/'bluetooth-startup-source-private.txt').read_text();old='/bin/insmod "$path"';assert source.count(old)==1
source=source.replace('''    for module in btbcm btqca hci_uart; do''','''    /usr/bin/python3 /var/lib/samurai/k205-tools/boot-uart-trace.py start
    for module in btbcm btqca hci_uart; do''',1)
source=source.replace(old,'''if [ "$module" = hci_uart ]; then
                /bin/insmod "$path" samurai_rx_diag=1
            else
                /bin/insmod "$path"
            fi''')
helper=host.PRIVATE/'samurai-bluetooth-bootdiag-private.sh';helper.write_text(source);subprocess.run(['sh','-n',str(helper)],check=True)
host.upload(helper,'/var/lib/samurai/k205-tools/samurai-bluetooth-bootdiag.sh');host.upload(here/'boot-uart-trace.py','/var/lib/samurai/k205-tools/boot-uart-trace.py')
digest=hashlib.sha256(helper.read_bytes()).hexdigest();original_digest=hashlib.sha256((host.PRIVATE/'bluetooth-startup-source-private.txt').read_bytes()).hexdigest()
native=r'''
from pathlib import Path
import dbus,hashlib,json,os,shutil,subprocess
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k205-baseline/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert json.loads((root/'k205-uart-reprobe-r2/summary.json').read_text())['failed'] is False
bus=dbus.SystemBus(private=True);o=dbus.Interface(bus.get_object('org.bluez','/'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects();a=[v['org.bluez.Adapter1'] for v in o.values() if 'org.bluez.Adapter1' in v];assert len(a)==1 and not a[0]['Powered'] and not a[0]['Discovering'];assert not any(v.get('org.bluez.Device1',{}).get('Connected',False) for v in o.values());bus.close()
out=root/'k205-bootdiag-deploy';assert not out.exists();out.mkdir(mode=0o700)
helper=Path('/usr/sbin/samurai-bluetooth');assert hashlib.sha256(helper.read_bytes()).hexdigest()==OLD_HELPER;shutil.copyfile(helper,out/'samurai-bluetooth-original.sh')
module=Path('/usr/lib/modules')/os.uname().release/'kernel/drivers/bluetooth/hci_uart.ko';assert hashlib.sha256(module.read_bytes()).hexdigest()=='f6c5ed3538270480a72cf4bf8b1339103417941930b0d8ecb941fd11d16d7020';shutil.copyfile(module,out/'hci_uart185-original.ko')
build=json.loads((root/'k205-tools/diagnostic-build-validation.json').read_text());candidate=root/'k205-tools/hci_uart-k205-diagnostic-r2-private.ko';assert hashlib.sha256(candidate.read_bytes()).hexdigest()==build['candidate_sha256']
for target,data,mode in [(module,candidate.read_bytes(),0o644),(helper,(root/'k205-tools/samurai-bluetooth-bootdiag.sh').read_bytes(),0o755)]:
 temp=target.with_name(target.name+'.k205-new');temp.write_bytes(data);temp.chmod(mode);os.replace(temp,target)
assert hashlib.sha256(helper.read_bytes()).hexdigest()==NEW_HELPER
manifest=(root/'k200-deploy/paired-module-tree.sha256').read_text();needle='f6c5ed3538270480a72cf4bf8b1339103417941930b0d8ecb941fd11d16d7020';assert manifest.count(needle)==1
manifest=manifest.replace(needle,build['candidate_sha256']);(out/'paired-module-tree.sha256').write_text(manifest);assert len(manifest.splitlines())==784
subprocess.run(['sha256sum','-c',str(out/'paired-module-tree.sha256')],cwd=module.parents[3],check=True,stdout=(out/'module-check-private.log').open('wb'))
report=dict(stage=205,temporary_boot_diagnostic_staged=True,original185_module_and_helper_preserved=True,temporary_module_sha256=build['candidate_sha256'],temporary_boot_helper_sha256=NEW_HELPER,one_module_manifest_override=True,normal_runtime_not_restarted=True,boot_flash_not_requested=True)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
native=native.replace('OLD_HELPER',repr(original_digest)).replace('NEW_HELPER',repr(digest))
p=host.ssh('python3 -',input=native.encode(),timeout=45);(host.PRIVATE/'stage-bootdiag-private.log').write_bytes(p.stdout+p.stderr);(here/'boot-diagnostic-staging-validation.json').write_bytes(p.stdout);print(p.stdout.decode())
