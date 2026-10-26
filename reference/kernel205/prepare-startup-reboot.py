from pathlib import Path
import ast,json,subprocess

here=Path(__file__).resolve().parent;prior=here.parent/'kernel204/reboot-r2'
for name in ['collect-pre-reboot.py','stop-gnss-idle.py','quiesce-current183.sh','disable-crtc.py','check-quiesce.py','freeze-for-bootloader.sh','linux-restart2-bootloader.py','deploy-and-quiesce.py','reboot-current.py','refresh-usb-endpoint.ps1','collect-newboot.py','connect-newboot.py','fastboot-reboot-current.py']:
 source=(prior/name).read_text().replace('k204r2','k205').replace('kernel204/reboot-r2','kernel205').replace('stage=204','stage=205').replace("'stage': 204","'stage': 205").replace("['stage'] == 204","['stage'] == 205").replace("['stage']==204","['stage']==205")
 if name=='collect-pre-reboot.py':
  source=source.replace("root/'k204-runtime/boot-id-private.txt'","root/'k205-baseline/boot-id-private.txt'").replace("root/'k200-deploy/paired-module-tree.sha256'","root/'k205-bootdiag-deploy/paired-module-tree.sha256'")
  source=source.replace("watch['worker_starts']==watch['worker_completions']==0","watch['worker_starts']==watch['worker_completions']==1")
  source=source.replace("assert rp=={'adsp':'running','slpi':'offline','modem':'running'}\nassert json.loads(Path('/run/samurai-ssc/state.json').read_text())['stopped'] and Path('/sys/devices/platform/sensor-power/state').read_text().strip()=='vdd=0 vddio=0'","assert all(v=='running' for v in rp.values())\nassert json.loads(Path('/run/samurai-ssc/state.json').read_text())['started']")
  source=source.replace("dict(warning=0,oops=0,gpu=0,slpi_fatal=0,bluetooth=1)","dict(warning=0,oops=0,gpu=0,slpi_fatal=0,bluetooth=0)").replace('same_boot204_first_cycle=True','same_boot204r2=True')
  helper_hash=json.loads((here/'boot-diagnostic-staging-validation.json').read_text())['temporary_boot_helper_sha256'];source=source.replace("expected={'/usr/sbin/samurai-ssc'","expected={'/usr/sbin/samurai-bluetooth':'"+helper_hash+"','/usr/sbin/samurai-ssc'")
 if name=='reboot-current.py':
  source=source.replace("host.PRIVATE.parent/'transport-last-failure-private.log'","host.PRIVATE/'transport-last-failure-private.log'")
  # Our transport wrapper stores a unique failure log per disconnect.
  source=source.replace("output = (host.PRIVATE/'transport-last-failure-private.log').read_bytes()","output = max(host.PRIVATE.glob('transport-failure-*-private.log'),key=lambda p:p.stat().st_mtime_ns).read_bytes()")
 if name=='connect-newboot.py':
  source=source.replace("here.parent.parent/'kernel188/host.py'","here.parent/'kernel188/host.py'").replace("parent.parent.parent/'kernel188/host.py'","parent.parent/'kernel188/host.py'")
 if name=='fastboot-reboot-current.py':source=source.replace('host.PRIVATE.parents[1] /','host.PRIVATE.parent /')
 if name=='collect-newboot.py':
  source=source.replace('module_tree_784_files_exact=True','module_tree_784_files_exact_with_diagnostic_override=True').replace('reboot_cycle=2','reboot_cycle=1')
 if name.endswith('.py'):ast.parse(source)
 (here/name).write_text(source)
 if name.endswith('.sh'):subprocess.run(['sh','-n',str(here/name)],check=True)
print('Prepared one fresh-identity ordinary diagnostic startup; no flash path added.')
