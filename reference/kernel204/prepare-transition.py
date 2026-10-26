from pathlib import Path
import ast,hashlib,json,shutil,subprocess

here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel204');prior=here.parent/'kernel202/reboot-r2'
for name in ['collect-pre-reboot.py','stop-gnss-idle.py','quiesce-current183.sh','disable-crtc.py','check-quiesce.py','freeze-for-bootloader.sh','linux-restart2-bootloader.py','deploy-and-quiesce.py','reboot-current.py','refresh-usb-endpoint.ps1','collect-newboot.py','connect-newboot.py']:
 source=(prior/name).read_text().replace('k202r2','k204').replace('kernel202/reboot-r2','kernel204').replace('stage=202','stage=204').replace("'stage': 202","'stage': 204").replace("['stage'] == 202","['stage'] == 204").replace("['stage']==202","['stage']==204")
 if name=='collect-pre-reboot.py':
  source=source.replace("root/'k202-runtime/boot-id-private.txt'","root/'k204-baseline-r2/boot-id-private.txt'").replace('same_boot202_first_cycle=True','same_boot203=True')
  source=source.replace("watch['worker_starts']==watch['worker_completions']==0","watch['worker_starts']==watch['worker_completions']==1")
 if name=='quiesce-current183.sh':
  old='test "$(readlink -f /proc/$pid/exe)" = "$(readlink -f /usr/sbin/ModemManager)"'
  assert old in source
  source=source.replace(old,'test "$(sha256sum /proc/$pid/exe | cut -d\' \' -f1)" = b350c55ba334b7d23564136fe3ce19bf37f95db0d374f63cc89351341d9b9ddc')
 if name=='collect-newboot.py':
  source=source.replace("for name in ['partition', 'userspace']:","for name in ['userspace']:")
  insertion="""
expected_persist=json.loads((root/'k200-runtime/partition-hashes-private.json').read_text())['persist']
for dev,label,size,digest in [('sde11','boot',100663296,'cdd16e29f3639dd79fe7c1a98ac3a5fcb2827d701d2291af93a4da0884476082'),('sde32','logdump',67108864,'e73754c7d327925acf031aed54e0e6d02069b7a112c32b187ac9bfb468da1358'),('sda2','persist',None,expected_persist)]:
    path='/dev/'+dev;assert subprocess.check_output(['lsblk','-ndo','PARTLABEL',path],text=True).strip()==label
    if size:assert int(subprocess.check_output(['blockdev','--getsize64',path],text=True))==size
    assert subprocess.check_output(['sha256sum',path],text=True).split()[0]==digest,label
uart=Path('/sys/bus/platform/devices/c8c000.serial');assert (uart/'power/wakeup').read_text().strip()=='enabled'
assert (uart/'of_node/pinctrl-names').read_bytes()==b'default\\0sleep\\0'
assert not (uart/'of_node/interrupts').exists() and len((uart/'of_node/interrupts-extended').read_bytes())==28
(out/'uart-pm-private.json').write_text(json.dumps({n:(uart/n).read_text().strip() for n in ['power/wakeup','power/control','power/runtime_status']},indent=2)+'\\n')
"""
  anchor="for name in ['userspace']:\n";assert anchor in source;source=source.replace(anchor,insertion+anchor)
  source=source.replace('unchanged_boot200_logdump183_persist_and_nv=True','boot204_readback_and_logdump183_persist_nv_verified=True, uart_rx_wake_enabled=True, uart_sleep_state_present=True')
  source=source.replace('partitions_flashed=[]','partitions_flashed=[\'boot\']')
 if name=='connect-newboot.py':
  source=source.replace("here.parent.parent/'kernel188/host.py'","here.parent/'kernel188/host.py'").replace("parent.parent.parent/'kernel188/host.py'","parent.parent/'kernel188/host.py'")
 if name=='reboot-current.py':source=source.replace('One ordinary bootloader round trip; no partition flash.','One bootloader transition; flash uses a separate fresh identity gate.').replace('flash_requested=False','flash_requested=True')
 if name.endswith('.py'):ast.parse(source)
 (here/name).write_text(source)
 for_shell=name.endswith('.sh')
 if for_shell:subprocess.run(['sh','-n',str(here/name)],check=True)
source=(here.parent/'kernel200/flash-boot.py').read_text().replace('stage=200','stage=204').replace('boot-partition-k200-mmcx.img','boot-partition-k204-bt-wake.img').replace('boot-rollback-k172-private.img','boot-rollback-k200-private.img')
ast.parse(source);(here/'flash-boot.py').write_text(source)
target=private/'boot-rollback-k200-private.img';assert not target.exists();shutil.copyfile(private.parent/'kernel200/boot-partition-k200-mmcx.img',target)
assert hashlib.sha256(target.read_bytes()).hexdigest()=='5109097b74aafd38838174f31fbff2d8c940977fdc4982658ebe86f671d1e1f0'
print('Prepared fresh-identity transition, mapped-MM hash guard, boot200 rollback, and boot204 runtime checks; no transition submitted.')
