"""Record the completed second ordinary reboot without replaying it."""
from pathlib import Path
import json
import host

here = Path(__file__).resolve().parent
restart = json.loads((host.PRIVATE / 'reboot-request-private.json').read_text())
normal = json.loads((host.PRIVATE / 'fastboot-reboot-private.json').read_text())
assert restart['request_count'] == normal['request_count'] == 1
prior = host.PRIVATE / 'usb-ipv6-candidates-private.json'
backup = host.PRIVATE / 'usb-ipv6-before-reboot-private.json'
assert not backup.exists()
prior.rename(backup)
for folder in (host.PRIVATE, host.PRIVATE.parent):
    target = folder / 'current-work-private.json'
    plan = json.loads(target.read_text())
    plan.update(state='Second207 full quiesce and archive passed. One RESTART2 path and one freshly identified fastboot ordinary reboot completed; no flash. Await fresh USB discovery and Linux boot identity.',
        transition_pending=False, reboot_sent=True,
        current_boot_guard='Not yet verified; do not reuse first207 boot guard.',
        current_host='reference/kernel207/reboot-r2/host.py after fresh discovery',
        next='Discover scoped USB peer and run connect-newboot.py once; inspect the same boot if observation fails. Do not replay transition scripts.')
    target.write_text(json.dumps(plan, indent=2) + '\n')
next_file = here.parents[2] / 'NEXT-SESSION.md'
text = next_file.read_text()
text = text.replace('## 当前部署', '第二次207普通重启已发出并验证fastboot身份，未刷写。MCFG自动加载验证待新USB/newboot收据；当前使用reference/kernel207/reboot-r2/host.py，不得重用首轮boot身份或重放切换。\n\n## 当前部署', 1)
next_file.write_text(text)
print('Second207 transition recorded; old scoped endpoint preserved. Fresh boot observation pending.')
