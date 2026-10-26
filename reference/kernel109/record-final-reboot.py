from pathlib import Path
import json
root=Path('/mnt/e/RealmeX2Pro edk2')
report=json.loads((root/'reference/kernel109/checkpoint-validation.json').read_text())
assert report['early_ssh_and_rc_logger_latest_normal_reboot_pass']
note=f'''
新增UCM后的第二次正常重启曾运行约370秒而USB网络未恢复；取得F1回执、独立fastboot核验后只reboot同#109，没有新刷写，Phosh/NM/NTP/音频自动恢复。随后把NCM/SSH提前到boot并启用持久rc.log，第三次正常重启与文件/HTTPS/校时/Phosh/UCM空闲关闭回归通过。最新显示完成超时{report['latest_reboot_display_timeouts']}/GPU故障{report['latest_reboot_gpu_faults']}/taint0、AW8697 starts0；超时在128.02秒、Phosh启动后出现，最新截图仍成功。那次重启失败原因及显示/重启长稳仍待定位，不能说已彻底解决。已构建审计#110诊断救援候选（不挂userdata、不自动启动radio），尚未部署，当前仍#109。
'''
for name in ['README.md','FLYWHEEL.md','NEXT-SESSION.md','linux-port/docs/HARDWARE-STATUS.md']:
    path=root/name;text=path.read_text()
    needle='全硬件goal active。'
    pos=text.index(needle)+len(needle)
    text=text[:pos]+'\n'+note+text[pos:]
    text=text.replace('最新启动显示完成超时0/GPU故障0/taint0',
        f"首次持久重启检查点显示超时0/GPU故障0/taint0；最新检查点显示超时{report['latest_reboot_display_timeouts']}/GPU故障{report['latest_reboot_gpu_faults']}/taint0")
    text=text.replace('第二次正常重启正在检验UCM自动恢复；新boot获取完整dmesg/Phosh/PA/PCM/功放和联网校时状态，用全新目录/前缀导出并校验。初次rootfs持久重启已通过，第二次结果必须按新证据更新文档。',
        '最新第三次正常重启已核验Phosh/UCM/NM/NTP与文件持久化；第二次失败及F1恢复记录保留。继续定位启动/重启稳定性，新的实验仍需新目录/前缀和完整日志。')
    text=text.replace('最新重启自动音频回归继续','最新重启已自动恢复桌面音频，空闲PCM/功放关闭')
    path.write_text(text)
path=root/'sessions/109-pmos-userdata-phosh-and-desktop-audio.md';text=path.read_text()
text=text.replace('第二次正常重启正在验证新增UCM的自动恢复，结果应追加独立检查点。',
    '第二次正常重启未恢复USB网络，已由F1→fastboot仅重启同镜像恢复；启用boot阶段NCM/SSH与持久rc.log后，第三次正常重启独立核验通过。失败原因和长稳未验收。')
text+='\n## 最后实机状态\n'+note
path.write_text(text)
print('LATEST_NORMAL_REBOOT_PASS_AND_PRIOR_FAILURE_RECORDED')
