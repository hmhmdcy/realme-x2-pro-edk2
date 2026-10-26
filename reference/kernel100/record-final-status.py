from pathlib import Path
import json

root=Path('/mnt/e/RealmeX2Pro edk2')
out=Path('/mnt/e/edk2-samurai-out/kernel100')
final=json.loads((out/'final-status-validation.json').read_text())
assert final['final_status_audit_pass'] and final['additional_display_timeouts']==1
assert final['display_frame_done_timeout_uptimes']==[321.625858,438.714099,443.047118]
for name in ('README.md','FLYWHEEL.md','linux-port/README.md','linux-port/docs/HARDWARE-STATUS.md'):
    path=root/name;text=path.read_text()
    assert text.count('本次两次显示超时')==1
    path.write_text(text.replace('本次两次显示超时','本次三次显示超时'))
path=root/'linux-port/docs/HARDWARE-STATUS.md';text=path.read_text()
old='#99两次frame-done timeout在321.63/438.71秒，最终underrun0/frame_done_cnt2'
new='#99 checkpoint两次超时321.63/438.71秒，underrun0/frame_done_cnt2；最后只读状态又见443.05秒第三次'
assert old in text;text=text.replace(old,new)
old='CDC NCM/high-speed、Windows系统UsbNcm、自动密钥SSH/SCP及EUD共存已实测，双向4MiB校验通过'
assert old in text;text=text.replace(old,old+'；本轮两次SCP超时保留，80个备份块降低速率后校验通过')
path.write_text(text)
path=root/'reference/kernel100/next-session.md';text=path.read_text()
old='本次两次显示超时321.625858/438.714099秒，underrun0/frame_done_cnt2'
assert old in text
text=text.replace(old,'本次累计三次显示超时321.625858/438.714099/443.047118秒；86文件checkpoint时underrun0/frame_done_cnt2，最后8文件又记录第三次')
addition=f"最后8文件只读状态在uptime {final['uptime_seconds']:.2f}秒验证同一次boot：MPSS running、5GHz COMPLETED、BT关闭、振动standby、taint0，NV/persist不变，无额外MPSS fatal，但显示新增一次超时；原包SHA `{final['archive_sha256']}`，私人final-status-validation.json。\n\n"
anchor='阶段100 Image SHA '
assert anchor in text;text=text.replace(anchor,addition+anchor)
path.write_text(text)
(root/'NEXT-SESSION.md').write_text(text.replace('../../sessions/','sessions/').replace('../../linux-port/','linux-port/'))
path=root/'NEXT-SESSION-PROMPT.md';text=path.read_text()
assert '本次两显示超时' in text
path.write_text(text.replace('本次两显示超时','本次三显示超时'))
path=root/'sessions/100-all-source-readiness-and-first-mpss-crash.md';text=path.read_text()
text=text.replace('当前启动两次显示超时','86文件checkpoint时记录两次显示超时')
text=text.replace('显示最终underrun0/frame_done_cnt2','checkpoint显示underrun0/frame_done_cnt2')
anchor='私有目录 `E:/edk2-samurai-out/kernel100`'
assert anchor in text
text=text.replace(anchor,addition+anchor)
path.write_text(text)
path=root/'reference/kernel100/README.md';text=path.read_text()
text+='\n'+addition
path.write_text(text)
print('ADDITIONAL_DISPLAY_TIMEOUT_RECORDED_WITH_FINAL_STATUS')
