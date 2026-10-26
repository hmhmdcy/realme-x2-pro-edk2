from pathlib import Path
import host, json
here = Path(__file__).resolve().parent; repo = here.parents[1]
restart = json.loads((host.PRIVATE / 'reboot-request-private.json').read_text())
normal = json.loads((host.PRIVATE / 'fastboot-reboot-private.json').read_text())
assert restart['request_count'] == normal['request_count'] == 1
prior = host.PRIVATE / 'usb-ipv6-candidates-private.json'
backup = host.PRIVATE / 'usb-ipv6-before-reboot-private.json'
assert not backup.exists(); prior.rename(backup)
plan_path = host.PRIVATE / 'current-work-private.json'
plan = json.loads(plan_path.read_text())
plan.update(state='Full quiesce/archive passed. Single RESTART2 path and freshly verified fastboot ordinary reboot completed. Await new USB peer and fresh Linux boot identity; no flash.', transition_pending=False, reboot_sent=True, old_boot_guard='/var/lib/samurai/k207-before-reboot/boot-id-private.txt', current_boot_guard='Not yet verified; do not use the old guard for a new transition.', next='Discover fresh scoped USB peer, run connect-newboot collector. If observation fails, inspect same boot; do not repeat reboot.')
plan_path.write_text(json.dumps(plan, indent=2) + '\n')
next_file = repo / 'NEXT-SESSION.md'
text = next_file.read_text().replace('当前仍205第二次启动，207尚未重启或刷写；当前运输reference/kernel207/host.py，guard为/var/lib/samurai/k207-baseline/boot-id-private.txt（与k205r2-runtime相同）。', '207已完成quiesce/归档、单次RESTART2和fresh fastboot普通reboot，未刷写。正在核对新USB与新boot，当前不能用k207-baseline旧身份再次切换。reference/kernel207/host.py须等待新peer记录后使用。')
text = text.replace('当前准备一次普通新启动以观察真实mcfg.tmp工作文件/PDC/GNSS；尚未发切换。', '普通重启请求已完成一次，正在观察新启动的mcfg.tmp/PDC/GNSS；不得重发切换。')
next_file.write_text(text)
print('Single ordinary reboot recorded; old endpoint preserved, fresh discovery required.')
