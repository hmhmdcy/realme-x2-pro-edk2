from pathlib import Path
import ast,hashlib,json

here=Path(__file__).resolve().parent;dest=here/'reboot-r2';assert not dest.exists();dest.mkdir()
private=Path('/mnt/e/edk2-samurai-out/kernel204/reboot-r2');private.mkdir(mode=0o700)
for name in ['collect-pre-reboot.py','stop-gnss-idle.py','quiesce-current183.sh','disable-crtc.py','check-quiesce.py','freeze-for-bootloader.sh','linux-restart2-bootloader.py','deploy-and-quiesce.py','reboot-current.py','refresh-usb-endpoint.ps1','collect-newboot.py','connect-newboot.py']:
 source=(here/name).read_text().replace('k204','k204r2').replace('kernel204','kernel204/reboot-r2')
 # Inherited names refer to cycle-1 files when establishing the current identity.
 if name=='collect-pre-reboot.py':
  source=source.replace("root/'k204r2-baseline-r2/boot-id-private.txt'","root/'k204-runtime/boot-id-private.txt'")
  source=source.replace('5109097b74aafd38838174f31fbff2d8c940977fdc4982658ebe86f671d1e1f0','cdd16e29f3639dd79fe7c1a98ac3a5fcb2827d701d2291af93a4da0884476082')
  source=source.replace("watch['worker_starts']==watch['worker_completions']==1","watch['worker_starts']==watch['worker_completions']==0").replace("watch['time_preparation_starts']==watch['time_preparation_completions']==1","watch['time_preparation_starts']==watch['time_preparation_completions']>=1")
  source=source.replace("assert all(v=='running' for v in rp.values())","assert rp=={'adsp':'running','slpi':'offline','modem':'running'}\nassert json.loads(Path('/run/samurai-ssc/state.json').read_text())['stopped'] and Path('/sys/devices/platform/sensor-power/state').read_text().strip()=='vdd=0 vddio=0'")
  source=source.replace('assert not any(counts.values())',"assert counts==dict(warning=0,oops=0,gpu=0,slpi_fatal=0,bluetooth=1)").replace('same_boot203=True','same_boot204_first_cycle=True').replace('boot200_logdump183_and_persist_readback_exact=True','boot204_logdump183_and_persist_readback_exact=True')
  ssc_hash=json.loads((here/'ssc-observation-validation.json').read_text())['source_sha256']
  source=source.replace("'/usr/bin/ModemManager':","'/usr/sbin/samurai-ssc':'"+ssc_hash+"','/usr/bin/ModemManager':")
 if name=='stop-gnss-idle.py':source=source.replace("state['time_preparation_starts']==state['time_preparation_completions']==1","state['time_preparation_starts']==state['time_preparation_completions']>=1")
 if name=='reboot-current.py':source=source.replace('flash_requested=True','flash_requested=False')
 if name=='connect-newboot.py':
  source=source.replace("here.parent/'kernel188/host.py'","here.parent.parent/'kernel188/host.py'").replace("parent.parent/'kernel188/host.py'","parent.parent.parent/'kernel188/host.py'")
  source=source.replace("here.parent.parent.parent/'kernel188/host.py'","here.parent.parent/'kernel188/host.py'")
 if name=='collect-newboot.py':
  source=source.replace("partitions_flashed=['boot']","partitions_flashed=[], reboot_cycle=2")
 if name.endswith('.py'):ast.parse(source)
 (dest/name).write_text(source)
(dest/'host.py').write_text("from pathlib import Path\nimport importlib.util\nspec=importlib.util.spec_from_file_location('current204',Path(__file__).resolve().parent.parent/'host.py');transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport)\nssh,upload,download=transport.ssh,transport.upload,transport.download\nPRIVATE=Path('/mnt/e/edk2-samurai-out/kernel204/reboot-r2');PRIVATE.mkdir(mode=0o700,exist_ok=True)\n")
(dest/'run-native.py').write_bytes((here/'run-native.py').read_bytes())
source=(here.parent/'kernel202/reboot-r2/fastboot-reboot-current.py').read_text().replace('kernel202/reboot-r2','kernel204/reboot-r2')
ast.parse(source);(dest/'fastboot-reboot-current.py').write_text(source)
print('Prepared one ordinary reboot with fresh boot204 identity and preserved initial BT/SSC failures; no flash.')
