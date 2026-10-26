"""Retarget the already validated quiesce/bootloader path to fresh228 evidence."""
from pathlib import Path
import ast
import json

ref = Path(__file__).resolve().parent
for name in ['quiesce-current183.sh', 'stop-gnss-idle.py', 'quiesce-camera.py', 'disable-crtc.py',
             'check-quiesce.py', 'freeze-for-bootloader.sh', 'linux-restart2-bootloader.py', 'reboot-current.py']:
    text = (ref.parent / 'kernel219' / name).read_text()
    text = text.replace('k219-before-reboot', 'k228-baseline').replace('k219', 'k228').replace('stage=219', 'stage=228')
    text = text.replace("'stage': 219", "'stage': 228").replace("['stage'] == 219", "['stage'] == 228")
    text = text.replace('k228-reboot-tools', 'k228-tools')
    text = text.replace('"$before/module-tree.sha256"', '/var/lib/samurai/k228-module-install/module-tree-after.sha256')
    text = text.replace('/var/lib/samurai/k228-baseline/module-tree.sha256', '/var/lib/samurai/k228-module-install/module-tree-after.sha256')
    assert 'k219' not in text
    assert not (ref / name).exists()
    if name.endswith('.py'):
        ast.parse(text, filename=name)
    (ref / name).write_text(text)
text = (ref.parent / 'kernel204/reboot-r2/fastboot-reboot-current.py').read_text()
text = text.replace("host.PRIVATE.parents[1] / 'kernel109/fastboot-identity.json'", "host.PRIVATE.parent / 'kernel109/fastboot-identity.json'")
(ref / 'fastboot-reboot-current.py').write_text(text)
text = (ref.parent / 'kernel219/refresh-usb-endpoint.ps1').read_text().replace('kernel219', 'kernel228').replace('K219_', 'K228_')
text = text.replace("if (Test-Path -LiteralPath $taskDest) {throw 'Current discovery already recorded; inspect before changing'}",
                    "if (Test-Path -LiteralPath $taskDest) { Copy-Item -LiteralPath $taskDest -Destination \"$taskPrivate/usb-peer-before-postboot-refresh-private.json\" -ErrorAction Stop }")
(ref / 'refresh-usb-endpoint.ps1').write_text(text)
print(json.dumps(dict(stage=228, transition_helpers_prepared=True, module_tree_checks_use_candidate_inventory=True,
                     reference_bootloader_path=219, flash_requested=False, transition_sent=False)))
