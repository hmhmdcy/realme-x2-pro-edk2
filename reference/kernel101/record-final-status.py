from pathlib import Path
import json
root=Path('/mnt/e/RealmeX2Pro edk2')
out=Path('/mnt/e/edk2-samurai-out/kernel101')
r=json.loads((out/'final-status-validation.json').read_text())
assert r['final_status_audit_pass'] and r['verified_files']==8
text=f"最后8文件只读状态在uptime {r['uptime_seconds']}秒确认同一次#100启动：MPSS/ADSP running、5GHz COMPLETED、BT四标志关闭、振动standby/starts0、taint0、NV/persist不变；累计MPSS fatal1、ADSP fatal0、显示超时0、BT phase2错误3，无额外MPSS fatal。原包SHA `{r['archive_sha256']}`，私人final-status-validation.json；版本为本次原生查询后的缓存，未重复发送查询。\n"
assert not (out/'final-status-doc-recorded').exists()
for name in ('reference/kernel101/README.md','reference/kernel101/next-session.md','sessions/101-adsp-native-apr-reply-and-radio-regression.md'):
    p=root/name
    p.write_text(p.read_text()+'\n'+text)
p=root/'NEXT-SESSION.md'
p.write_text((root/'reference/kernel101/next-session.md').read_text().replace('../../sessions/','sessions/').replace('../../linux-port/','linux-port/'))
(out/'final-status-doc-recorded').write_text('1\n')
print('FINAL_READONLY_STATUS_RECORDED')
