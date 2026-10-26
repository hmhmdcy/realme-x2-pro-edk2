from pathlib import Path
import ast,json

here=Path(__file__).resolve().parent;dest=here/'reboot-r2';assert not dest.exists();dest.mkdir();private=Path('/mnt/e/edk2-samurai-out/kernel205/reboot-r2');private.mkdir(mode=0o700)
for name in ['collect-pre-reboot.py','stop-gnss-idle.py','quiesce-current183.sh','disable-crtc.py','check-quiesce.py','freeze-for-bootloader.sh','linux-restart2-bootloader.py','deploy-and-quiesce.py','reboot-current.py','refresh-usb-endpoint.ps1','collect-newboot.py','connect-newboot.py','fastboot-reboot-current.py']:
 source=(here/name).read_text().replace('k205','k205r2').replace('kernel205','kernel205/reboot-r2')
 source=source.replace('k205r2-bootdiag-deploy','k205-bootdiag-deploy')
 if name=='collect-pre-reboot.py':
  source=source.replace("root/'k205r2-baseline/boot-id-private.txt'","root/'k205-runtime/boot-id-private.txt'").replace("watch['worker_starts']==watch['worker_completions']==1","watch['worker_starts']==watch['worker_completions']==0").replace('same_boot204r2=True','same_boot205_first_cycle=True')
  old=json.loads((here/'boot-diagnostic-staging-validation.json').read_text())['temporary_boot_helper_sha256'];new=json.loads((here/'error-only-staging-validation.json').read_text())['error_only_boot_helper_sha256'];source=source.replace(old,new)
 if name=='connect-newboot.py':
  source=source.replace("here.parent/'kernel188/host.py'","here.parent.parent/'kernel188/host.py'")
  source=source.replace("Path(__file__).resolve().parent.parent/'kernel188/host.py'","Path(__file__).resolve().parent.parent.parent/'kernel188/host.py'")
 if name=='fastboot-reboot-current.py':source=source.replace('host.PRIVATE.parent /','host.PRIVATE.parents[1] /')
 if name=='reboot-current.py':source=source.replace("host.PRIVATE.glob('transport-failure-*-private.log')","host.PRIVATE.parent.glob('transport-failure-*-private.log')")
 if name=='collect-newboot.py':source=source.replace('reboot_cycle=1','reboot_cycle=2')
 if name.endswith('.py'):ast.parse(source)
 (dest/name).write_text(source)
(dest/'host.py').write_text("from pathlib import Path\nimport importlib.util\nspec=importlib.util.spec_from_file_location('current205',Path(__file__).resolve().parent.parent/'host.py');transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport)\nssh,upload,download=transport.ssh,transport.upload,transport.download\nPRIVATE=Path('/mnt/e/edk2-samurai-out/kernel205/reboot-r2');PRIVATE.mkdir(mode=0o700,exist_ok=True)\n")
(dest/'run-native.py').write_bytes((here/'run-native.py').read_bytes())
print('Prepared second ordinary startup with error-only diagnostics and no UART trace overhead; no flash.')
