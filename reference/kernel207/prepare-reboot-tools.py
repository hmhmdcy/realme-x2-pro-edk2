from pathlib import Path
import ast
here = Path(__file__).resolve().parent
old = here.parent / 'kernel205/reboot-r2'
names = ['quiesce-current183.sh', 'stop-gnss-idle.py', 'disable-crtc.py', 'check-quiesce.py', 'freeze-for-bootloader.sh', 'linux-restart2-bootloader.py', 'deploy-and-quiesce.py', 'reboot-current.py', 'fastboot-reboot-current.py', 'collect-newboot.py', 'connect-newboot.py', 'refresh-usb-endpoint.ps1']
for name in names:
    target = here / name; assert not target.exists()
    source = (old / name).read_text().replace('kernel205/reboot-r2', 'kernel207').replace('k205r2', 'k207').replace('stage=205', 'stage=207').replace("'stage': 205", "'stage': 207").replace("['stage'] == 205", "['stage'] == 207")
    if name == 'fastboot-reboot-current.py': source = source.replace('host.PRIVATE.parents[1]', 'host.PRIVATE.parent')
    if name == 'reboot-current.py':
        start = source.index('    # The inherited privacy wrapper')
        end = source.index("(host.PRIVATE/'restart-submit-private.log')", start)
        source = source[:start] + "    last = host.PRIVATE/'transport-last-failure-private.log'\n    assert last.exists()\n    output = last.read_bytes()\n" + source[end:]
    if name == 'collect-newboot.py':
        source = source.replace('module_tree_784_files_exact_with_diagnostic_override=True', 'original_module_tree_784_files_exact=True')
        source = source.replace('reboot_cycle=2', 'reboot_cycle=1')
        source = source.replace('deadline=time.monotonic()+75', 'deadline=time.monotonic()+100')
        source = source.replace("helper_and_mm191_exact=True,", "helper_and_mm191_exact=True,new_tftp_and_wifi_helper_exact=True,")
    if name == 'connect-newboot.py':
        source = source.replace("here.parent.parent/'kernel188/host.py'", "here.parent/'kernel188/host.py'")
        source = source.replace("Path(__file__).resolve().parent.parent.parent/'kernel188/host.py'", "Path(__file__).resolve().parent.parent/'kernel188/host.py'")
        source = source.replace('timeout=160', 'timeout=200')
    if name.endswith('.py'): ast.parse(source)
    target.write_text(source)
print('Prepared guarded ordinary reboot and new-boot collector; no transition or flash sent.')
