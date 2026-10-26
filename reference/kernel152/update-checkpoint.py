from pathlib import Path
import json,shutil
root=Path('/mnt/e/RealmeX2Pro edk2')
archive=root/'archive'
for name in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md']:
    dst=archive/(name.removesuffix('.md')+'-through151-2026-10-13.md')
    assert not dst.exists()
    shutil.copy2(root/name,dst)
checkpoint='''# Realme X2 Pro 当前检查点

2026-10-13，阶段152。**永久显示修复仍开放；152候选拒收，已回退147并恢复实体桌面。** 当前规则只以[WORKING-BOUNDARIES](WORKING-BOUNDARIES.md)为准。

## 当前实际状态

当前内核#147、boot132/logdump147/modules132、software132加Mesa149修复库。本轮是回退后的新boot，旧151/149启动身份已成为历史，不能复用。源码仍在WSL`/home/cy122/pmos-samurai-kernel136/kernel`；DSI源码已撤回147，生成的Image仍是拒收152，不能直接打包当147。新身份只在私有kernel152/rollback147-closeout及手机`/var/lib/samurai/k152-rollback147-closeout`。

147新boot也复现boot CTL shutdown -22、首次无DRM/Phosh；一次有界面板重新探测和原initial_session恢复DRM/Phosh，用户确认实体屏幕显示桌面。40.45秒九次收尾taint0、DPU/DSI/GPU/WARN0、音频DMA prepare70，计数保持；bootstrap KMS失败日志仍保留，不能由DPU timeout0宣称启动显示无故障。恢复后DRM card索引可能变为0，以by-path解析，不能硬编码card1。

实际logdump147读回及boot/persist/132模块树/NV来源校验通过，Mesa149库SHA保持`97f3638851b534070f649fabfbdbb3d330b4ad0e2b0ea93b78026ad71d78fb5e`。152临时启动服务已移除，没有自建k152-startup实例。[收尾](reference/kernel152/rollback-closeout-validation.json)、[会话](sessions/152-display-lifecycle-candidate-and-boot-handoff-reproduction.md)

## 152结果与下一项

152修改DSI错误worker与DMA/关屏/电源的串行化，并在IRQ关闭后取消pending work；九个实际函数14项普通及ASAN/UBSAN通过，完整Image/DTB/770模块/FAT/checkpatch通过。原147的24次DisplayConfig正常电源转换通过。但真实152启动出现UFS UIC/SCSI阻塞和CTL接管失败，355秒后仅进入诊断RAM，未挂userdata/F2FS，实体黑屏，因此拒收。

该boot F1已受理，但device_shutdown也被异步存储探测阻塞。保存SysRq w与完整日志、核实当前boot/RAM-only后一次SysRq b完成挂起切换，真实bootloader身份/产品/几何重新核实后只刷回147。回退147重复CTL失败，不能凭候选失败断言新增DSI锁导致它。一次panel reprobe成功只是临时恢复。[失败与恢复](reference/kernel152/README.md)

新优先线索：SOFEF03F probe在mipi_dsi_attach/component_add之前assert reset并关闭VCI/VDDD，而DPU启动CTL清理发生在后面。计划独立验证probe使用GPIOD_ASIS保持固件面板电平，prepare才配置GPIO方向与初始状态，并保留完整原厂DSC、上电和reset序列；不把panel直接标成prepared，不混入152同步补丁。DT默认pinctrl没有output-high/low属性。此项尚属源码线索，未经实机A/B确认。[研究](reference/kernel152/internet-findings.md)

wlr-randr --off曾移除唯一逻辑输出并造成Phosh空monitor崩溃，已恢复；应使用当前会话DisplayConfig.PowerSaveMode进行电源测试。wlopm在当前Phoc被拒绝。152采集失败原件、候选启动与回退日志均保留，不伪装为通过。

## GPU及其它待办保持

147/149已复现GPU CCU故障的修复结论保持；本轮核对修复库但没有重新跑GPU专项压力。150无Mesa本地补丁降级候选仍未部署。Mesa升级或恢复旧rootfs132会覆盖本地库，后续软件包和完整rootfs需携带0015补丁。151记录的包数据库与149摘要差异原因仍未建立，不能声称软件数据库全部不变。历史GPU细节见[151检查点](archive/NEXT-SESSION-through151-2026-10-13.md)。

充电控制/保护、音频首次DMA/停止链、实体camera、完整传感器、蜂窝、GNSS、指纹、NFC和休眠长稳继续开放。[硬件清单](linux-port/docs/HARDWARE-STATUS.md)。保护重要分区/NV/校准/工厂备份；不操作FET/OTP/unseal或绕过温控；BT只扫描不连接，振动不新增脉冲。当前切换要用新状态证据，不复用旧身份或在状态未知时重复切换。
'''
(root/'NEXT-SESSION.md').write_text(checkpoint)
(root/'NEXT-SESSION-PROMPT.md').write_text('''继续Realme X2 Pro显示修复，先读NEXT-SESSION.md、reference/kernel152/README.md和WORKING-BOUNDARIES.md。152 DSI同步候选真实启动失败，已撤回源码并回退147；147新boot也复现CTL -22，单次panel reprobe和原initial_session恢复实体桌面，用户已确认。40.45秒九次taint0、DPU/DSI/GPU/WARN0、DMA prepare70保持，logdump147/boot/persist/模块/NV/Mesa149库核对通过，临时152启动服务已移除。新boot身份只用kernel152私有收尾；DRM card按by-path解析。源码DSI为147，生成Image仍152，不能混用。

下一项独立验证SOFEF03F probe过早assert reset/关闭VCI/VDDD这一源码缺陷：它发生在mipi_dsi_attach/component_add和DPU boot CTL清理之前。probe保持GPIO，prepare才设置方向与电平，保留原厂供电/DSC/复位和失败收尾，不直接设置prepared，不混入152补丁。先真实函数/错误路径与完整构建，再新启动验证。152存在UFS阻塞和RAM诊断fallback，F1 shutdown也被存储探测卡住；已保存现场并在确认无F2FS后一次SysRq b回退，不重放旧切换。wlr-randr --off引发用户态monitor崩溃，电源测试改用DisplayConfig。

GPU147/149修复保持，150降级未部署；Mesa包/新rootfs携带0015、包数据库差异及其它硬件待办保留。显示永久修复仍未完成，goal active。
''')
p=root/'linux-port/docs/HARDWARE-STATUS.md'
s=p.read_text().replace('最后核对：2026-10-13，阶段151。','最后核对：2026-10-13，阶段152。')
s=s.replace('以[本轮收尾收据](../../reference/kernel151/closeout.json)', '以[本轮显示回退收据](../../reference/kernel152/rollback-closeout-validation.json)')
s=s.replace('| 原生显示 | 原生60Hz输出、触摸桌面可用；当前窗口DPU/DSI计数0 | 首次接管超时、DSI欠载与历史滚动花屏缺少永久修复验收；开关屏、休眠、持续绘制长稳 |',
    '| 原生显示 | 147新boot单次面板reprobe恢复DRM/Phosh，用户确认实体桌面；原147的24次DisplayConfig电源转换通过 | 152及回退147均复现首次CTL -22，永久接管/DSI修复未验收；优先验证probe GPIO过早关断；休眠与长期绘制仍待办 |')
s=s.replace('SLIMbus首次DMA准备失败和停止生命周期；','152回退147启动DMA prepare70仍存在；SLIMbus首次DMA准备失败和停止生命周期；')
p.write_text(s)
p=root/'DOCS-INDEX.md';s=p.read_text()
marker='当前进展与交接：'
i=s.index(marker);end=s.index('\n\n',i)
s=s[:i]+'''当前进展与交接：[阶段152显示候选与真实回退](sessions/152-display-lifecycle-candidate-and-boot-handoff-reproduction.md)、[检查点](NEXT-SESSION.md)和[硬件清单](linux-port/docs/HARDWARE-STATUS.md)。现机为回退后的新147/software132加Mesa149库；152候选拒收，147同样首次CTL失败，单次面板reprobe恢复实体桌面。永久显示修复仍开放，下一项验证probe GPIO过早关断；源码DSI已147，生成Image仍152，不能混用。[152证据](reference/kernel152/README.md)。GPU147/149修复结论保持。'''+s[end:]
p.write_text(s)
print('K152_CURRENT_CHECKPOINT_UPDATED',flush=True)
