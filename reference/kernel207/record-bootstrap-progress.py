from pathlib import Path
import host, json
here = Path(__file__).resolve().parent; repo = here.parents[1]
for label, target in [('inspect-bootstrap', 'bootstrap-validation'), ('inventory-stock-mcfg', 'stock-mcfg-inventory-validation')]:
    value = json.loads((host.PRIVATE / (label + '-host-private.log')).read_text())
    (here / (target + '.json')).write_text(json.dumps(value, indent=2) + '\n')
assert json.loads((here / 'runtime-validation.json').read_text())['new_boot_identity_verified']
plan_path = host.PRIVATE / 'current-work-private.json'; plan = json.loads(plan_path.read_text())
plan.update(state='First207 normal boot verified. NewTFTP/RAMcache autostarted; MCFG temp operations progressed to missing readonly mdtime.txt. Same-handset read-only modem inventory found173 MCFG files including requested12-byte mdtime.', current_boot_guard='/var/lib/samurai/k207-runtime/boot-id-private.txt', current_host='reference/kernel207/host.py', transition_pending=False, first207_boot_complete=True, next='Supply the missing same-handset stock MCFG readonly subtree in RAM, update startup helper, verify native readonly transfer, then prepare a NEW guarded reboot cycle if needed. Do not reuse first reboot markers.')
plan_path.write_text(json.dumps(plan, indent=2) + '\n')
p = repo / 'NEXT-SESSION.md'; text = p.read_text()
start = text.index('完整外设goal active。'); end = text.index('\n\n## 当前部署', start)
text = text[:start] + '完整外设goal active。首次207普通新启动已验证，当前运输reference/kernel207/host.py，guard=/var/lib/samurai/k207-runtime/boot-id-private.txt。无刷写，三个DSP running、taint/fault0，UTC自动准备8次完成、GPS尚未启用。k207-baseline/before-reboot属于旧boot，首轮切换已完成，不得重放。[206完整快照](archive/NEXT-SESSION-through206-2026-10-15.md)保留历史原文。' + text[end:]
start = text.index('普通重启请求已完成一次'); end = text.index('\n\n正常新boot', start)
text = text[:start] + '首次207已自动运行B3 TFTP和32MiB工作缓存；mcfg.tmp由EACCES转为可创建/读，但目前零字节，不能据此声称数据初始化完成。随后modem请求/readwrite之外的只读modem_pr/mcfg/configs/mcfg_sw/mdtime.txt，服务目录缺失。只读核对本机modem分区实际有173份MCFG文件共8,807,671字节，所需mdtime12字节存在，源分区已卸载且未写入。下一步补齐本机原厂只读MCFG目录到RAM和启动脚本，核对真实QRTR读取，再用新身份/新目录准备下一轮普通重启。' + text[end:]
p.write_text(text)
print('Fresh207 boot and missing stock MCFG subtree recorded; first reboot is complete, no second reboot requested.')
