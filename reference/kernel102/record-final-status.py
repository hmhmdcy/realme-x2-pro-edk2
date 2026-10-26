from pathlib import Path
import json
root=Path('/mnt/e/RealmeX2Pro edk2');out=Path('/mnt/e/edk2-samurai-out/kernel102')
v=json.loads((out/'final-status-validation.json').read_text())
assert v['final_readonly_archive_audit_pass'] and v['display_timeouts']==2 and v['bt_phase2_errors']==2
paragraph=f"最终9文件只读现场在uptime {v['uptime_seconds']}秒确认同一次#101启动：5GHz COMPLETED、MPSS/ADSP running、fatal0、taint0，WCD组件仍绑定，错功放组件解绑/两reset低，BT控制器移除、振动standby/starts0、NV/persist不变；显示超时2/BT phase2错误2，无新增fatal。原包SHA `{v['archive_sha256']}`，私人final-status-validation.json；全硬件goal保持active。\n"
for name in ('sessions/102-wcd934x-and-real-max98937-identification.md','reference/kernel102/README.md','reference/kernel102/next-session.md'):
    p=root/name;s=p.read_text();assert paragraph not in s;p.write_text(s+'\n'+paragraph)
s=(root/'reference/kernel102/next-session.md').read_text()
(root/'NEXT-SESSION.md').write_text(s.replace('../../sessions/','sessions/').replace('../../linux-port/','linux-port/'))
print('FINAL_READONLY_STATE_RECORDED')
