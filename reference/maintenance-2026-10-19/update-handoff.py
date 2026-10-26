"""Archive prior entrypoints and record a paused handoff, without changing hardware claims."""
from pathlib import Path
import hashlib,json,shutil

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
archive=ROOT/'archive/camera-before-handoff-2026-10-19'
old=json.loads((ROOT/'reference/kernel302/checkpoint-validation.json').read_text())
assert not archive.exists()
manifest={}
for name in old['files']:
    source=ROOT/name;raw=source.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==old['files'][name]['sha256'],name
    target=archive/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
    manifest[name]=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
(archive/'manifest.json').write_text(json.dumps(dict(reason='User-requested paused handoff and build cleanup',files=manifest),indent=2)+'\n')
(archive/'README.md').write_text('# 2026-10-19交接前检查点原件\n\n保存302结束时九个入口的逐字原件；当前交接见[维护记录](../../reference/maintenance-2026-10-19/README.md)。\n')

p=ROOT/'NEXT-SESSION.md';s=p.read_text()
s=s.replace('目标继续。','适配目标已暂停；本轮仅交接与空间清理。')
s=s.replace('接下来复用libipa AgcMeanLuminance，','恢复后先做同时曝光／增益恒EV阶跃（20000µs×2与10000µs×4），验证联合锁存与过渡帧；再复用libipa AgcMeanLuminance，')
s=s.replace('297等旧产物、k132776／248备份保留。','k132776／248备份保留；旧中间产物可用性见清理收据。')
s+='\n2026-10-19交接：[清理收据与恢复方法](reference/maintenance-2026-10-19/README.md)。旧WSL对象／静态库与E盘缓存／中间vmlinux副本已清；源码、当前构建卷、r24-r3／302输出及回退包保留。无手机实验，302所有采集已终态。\n'
p.write_text(s)
p=ROOT/'DOCS-INDEX.md';s=p.read_text().replace('| 当前续作建议、证据路径及脚本复用注意 | [240交接说明](reference/kernel240/HANDOFF.md) |','| 当前交接、清理收据、重建方法及续作顺序 | [2026-10-19交接](reference/maintenance-2026-10-19/README.md) |')
p.write_text(s)
for name in ['linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']:
    p=ROOT/name;data=json.loads(p.read_text())
    data['maintenance_handoff']=dict(date='2026-10-19',adaptation_goal_status='paused',
        actual_kernel_build=298,latest_experimental_candidate=302,phone_modified=False,
        record='reference/maintenance-2026-10-19/README.md',
        old_intermediate_build_files_removed=True,current_source_and_recovery_packages_preserved=True)
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
for name in ['linux-port/camera/README.md','linux-port/camera/kernel/README.md','reference/kernel276/OEM-TUNING.md','linux-port/docs/HARDWARE-STATUS.md']:
    p=ROOT/name
    import os
    link=os.path.relpath(HERE/'README.md',p.parent).replace('\\','/')
    p.write_text(f'2026-10-19交接：适配目标已暂停，实际#298／候选302及未验收范围保持；本轮仅文档与旧编译产物清理。[交接、保留产物与重建方法]({link})。以下实验结论按当时记录阅读。\n\n'+p.read_text())
(ROOT/'sessions/maintenance-2026-10-19.md').write_text('# 2026-10-19：暂停交接与主机编译产物清理\n\n用户要求更新文档完成交接，并清理WSL及C、E盘过时编译产物。实际手机#298、最新私人候选302及其960帧手动控制验收不变，未进行手机实验。删除清单、空间测量、保留内容和恢复步骤见[交接记录](../reference/maintenance-2026-10-19/README.md)。\n')
print('Archived nine exact302 entrypoints; updated paused handoff and next joint-control test.')
