from pathlib import Path

root=Path('E:/RealmeX2Pro edk2')
out=Path('E:/edk2-samurai-out/kernel181')
next_text='''# Realme X2 Pro 当前检查点

最后核对：2026-10-14，内核181已部署。PDR/父IRQ/离线IRQ清理修复后，初启动和一次真实ADSP停启通过，原生及桌面左右播放/拾音闭环通过。完整音频goal active，耳机实物/自动crash/长PM/跨启动/音质与保护仍开放。用户暂无耳机，不重复问。规则见[WORKING-BOUNDARIES](WORKING-BOUNDARIES.md)。

## 最后核对的部署与范围

| 项目 | 结果 |
| --- | --- |
| 当前组合 | kernel181/logdump181；boot/DTB172、software/modules132、Mesa149、UCM173保持，只刷logdump |
| 标识 | #181 SMP PREEMPT Oct14 22:56:05 CST；logdump 56aa1c463d118f9de8d5dbd2cad3dc6b2ab1ff9f36d4027c77d457520b702a55；Image ae0eb8e0de80540cfe4349870020c1370534975bc30d90190c59afdf1d6afd11 |
| 181最终 | 892.99秒同boot、taint0、ADSP running，单card/alsa-card和HiFi(Mic,Speaker)，PCM关闭，双功放13/13静音、16保存控件恢复，五consumer各1、两map/一MCLK、main cache-only=N，NGD suspended；NV/persist/boot/logdump/770模块132核验 |
| 初启动与ADSP | 181新boot48.76秒所列故障0；一次实际offline→running回收card/map/MCLK/供电、2旧name FD EIO，自动HiFi/录音恢复、无machine重绑；PDR/IRQ读/config/mask/ASoC等全0 |
| 声学 | 181原生左右0.9574/0.9327、桌面0.9575/0.9942，功放关闭参考区分，无削顶、gain及volume/mute保持；171用户双组滴声仍有效，181不是音乐音质验收 |
| 错误范围 | 181最终ring从0秒开始且有#181 banner，所列20项全boot0；不扩大成未列出的整机问题清零。178/180真实失败保留 |
| 180改动 | PDR锁外事务/回调、地址/世代/通知序列、明确取消旧注册；lookup退役对象保留至worker/QMI回调停止。WCD先同步停parent IRQ再清children。27 PDR+91 SLIM/MFD场景，15负对照；初启干净，但停启config72/mask6失败 |
| 181改动 | 仅已DOWN时将现有main MAPLE map设cache-only，软件IRQ清理后销毁，不同步到硬件；UP移除真实IO，IF无缓存策略保持。91场景/11负对照及相同PDR源27/6覆盖，总118场景/17负对照 |
| 176/177历史 | 176地址/managed清理及10次重绑、18旧句柄通过；177两例短时s2idle通过，仅s2idle、非deep STR。它们不能替代181重复PM/自动SSR验收 |
| 桌面端口 | callaudiod拥有端口选择并卸载Pulse自动切换模块，UCM四设备/四profile；实物插拔未验，不强制补载端口模块 |
| 显示/GPU | 165实屏/DPMS及147/149已测修复保持，181显示源保持163；冷启动/长期开放 |

依据：[181](reference/kernel181/README.md)、[180](reference/kernel180/README.md)、[179锁重现](reference/kernel179/README.md)、[178失败](reference/kernel178/README.md)、[177](reference/kernel177/README.md)、[176](reference/kernel176/README.md)、[171人工听音](reference/kernel171/README.md)。其它功能见[硬件清单](linux-port/docs/HARDWARE-STATUS.md)。

## 源码、产物与回退依据

- WSL `/home/cy122/pmos-samurai-kernel136/kernel` tracked11：原176十文件加PDR。当前MFD181源5c4469fb…、PDR180源9bed7403…，其余九音频源及15显示源163保持；[完整哈希](reference/kernel181/build-package-validation.json)。MFD/codec/PDR/QMI builtin，public ABI与770模块132兼容。
- 181 W=1/checkpatch、全编译/FAT回读通过；仅两个模块build-id差异，不替换模块树。boot172哈希77e1a272…、DTB172 22c1f2ad…保持。EDK2 BDS源码164/生成固件172/FdtBlob129保持，工作区不是pristine132。
- 当前/回退私件在E:/edk2-samurai-out/kernel181、180、176。logdump180 c5439e24…有config72/mask6；176 6e3ebbe7…有178已知SSR/初启动错误；175 cbeedef0…有reset NACK/-110。完整172/171 SD1原件保持，164/168是SD0，不混入当前验收。
- UCM173、Mesa149及0015补丁保持，更新包/旧rootfs132可能覆盖；UCM132原件保存在k173-source/私人173包。181当前身份在私人k181-all包与手机k181-final；181 preflash属于旧180，下一次切换必须重新取当前身份。

## 续作与已知风险

1. 已知受控ADSP重启缺陷现已一次通过，但要补活跃流/真实自动crash、较长和重复PM、跨启动；先读181当前收据和源码，不重跑已过场景只为扩大数量。保留完整音频目标。
2. 耳机/耳麦/按钮、音乐/人声、瞬态、保护仍未验。当前有播放/拾音证据，不是音频完全不能用；也不以编码音证明频响/声压平衡。见[AUDIO提示](AUDIO-NEXT-SESSION-PROMPT.txt)。
3. 178保存失败下界IRQ读27720/config144/mask12/ASoC6/PDR2，初启动另PDR3/config8/mask1，ring曾覆盖；180真实停启config72/mask6且失败，之后声学通过。181通过不重写旧收据。
4. 180一次F1 OUT无RX回执，确认仍Linux/解冻后诊断，串口重绑未恢复；AHB wait从0设11仍无RX，原因未定，04040404本身不足证明MMIO坏。备用Linux RESTART2路径在180/181成功，停止EUD串口并仅操作源码CSR_EUD_EN关闭，再按实际fastboot身份/产品/几何只刷logdump。181前置冻结JSON捕获；180提交JSON因USB先断开未捕获。未盲目重复F1。
5. 180 capture误标签176：脚本实际guard#180、录音boot逐字等于已验runtime180，派生标签更正且原包/旧分析保留。181全部版本标签为181。181预检打印文案有CURRENT176残留，执行guard/哈希/身份实际是180，不作版本证据。
6. 停机fbdev last-close曾恢复CRTC；临时关emulation/null modeset后复核fd关闭仍inactive，下一boot恢复Y。保护NV/校准/私人数据及电池边界，蓝牙只扫描，振动不加脉冲。
7. 历史172 debugfs name Oops、175 NACK、177 USB HS-PHY L2/Wi-Fi告警保留。新启动音频所列错误0不等于所有整机问题清零，按硬件清单分别推进。

历史与维护见[会话索引](sessions/INDEX.md)、[文档导航](DOCS-INDEX.md)。
'''
audio_text='''在 E:\\RealmeX2Pro edk2 继续原生Linux音频修复，goal active。先读NEXT-SESSION、WORKING-BOUNDARIES、HARDWARE-STATUS和reference/kernel181/README.md，再查180/179/178及177/176/175/174/173/172/171。

已部署kernel181/logdump181，boot/DTB172、模块/软件132、Mesa149、UCM173保持。#181 Oct14 22:56:05 CST；logdump 56aa1c463d118f9de8d5dbd2cad3dc6b2ab1ff9f36d4027c77d457520b702a55，Image ae0eb8e0de80540cfe4349870020c1370534975bc30d90190c59afdf1d6afd11。当前身份在私人181/k181-all-private.tar.gz和手机k181-final，181 preflash是旧180，下一次切换新取身份。WSL kernel136 tracked11完整哈希见181 build，MFD181/PDR180、其余九音频源和15显示源163保持，builtin及770模块132兼容。

发声已有171用户双组滴声确认。181一次实际ADSP offline→running通过，card/map/MCLK/供电回收、2旧name FD EIO，自动恢复HiFi(Mic,Speaker)、录音，无machine手工重绑；PDR/IRQ读/config/mask/ASoC/DMA/FIFO所列故障0。恢复后原生四例左右相关0.9574/0.9327、桌面paplay+parecord 0.9575/0.9942，关闭功放参考区分、无削顶，gain与sink/source volume/mute保持。不是音乐/人声音质、完整频响或绝对声压验收。

181最终892.99秒同boot、taint0、ADSP running，单CARD/alsa-card和HiFi，PCM关闭、功放13/13静音、16保存控件恢复、五consumer各1、两map/一MCLK、main cache-only=N、NGD suspended；NV/persist/boot/logdump/770模块核验。ring仍从0秒开始且含#181 banner，所列20项全boot0，不扩大未列整机问题清零。

180修PDR：事务/locator等待与client回调均退出list_lock；地址/结果快照和server世代，indication序列阻止旧查询覆盖新通知；旧peer DEL忽略，ACK原端点，真实/coalesced DOWN先释放旧资源。active注册在更换/删除/retire/release时明确complete(-ENETRESET)，lookup对象退役后保留至worker/QMI callback停完再free，error release和locator同步。完整PDR27/6，SLIM/MFD91/9，118场景/15负对照，W=1/checkpatch/全编译/FAT和模块兼容通过。

180仍实际停启失败：config72/mask6，其它所列PDR/IRQ读/ASoC等0。181在同步停parent IRQ后，仅sdev DOWN把现有main MAPLE map改cache-only做软件IRQ清理，随后销毁、不同步或重放；UP移除仍真实IO，IF无缓存策略保持。实际regcache/_regmap_read/write+MFD证明离线无硬件访问，缓存外读EBUSY且不改值，非法写错误保留，新UP map正常。181新91/11及同hash PDR27/6覆盖118/17；不把软件cache更新描述成硬件接受写入。

178失败下界IRQ27720/config144/mask12/ASoC6/PDR2，启动PDR3/config8/mask1，ring覆盖原日志封存；180失败也保留，181通过不覆盖旧收据。176的10重绑/18旧FD和177两短s2idle仍属各自组合，不能替代181自动crash/长PM/跨启动。

下一步补活跃流/自动crash恢复和较长重复PM、跨启动，再音质/瞬态/保护；耳机/耳麦/按钮有实物后验，用户暂无耳机不要重复问。callaudiod拥有端口选择，勿强制补载Pulse自动切换模块。研究参考Realme19781原厂接线与OnePlus hotdog SD1/GPIO140、UCM/麦克风方法；不套TFA9874参数到MAX98937。

180切换F1无RX回执，确认仍原Linux/解冻后诊断；重绑EUD写wait11仍无RX，原因未定。Linux RESTART2路径180/181已实际成功：新身份/完整停机/冻结，停止EUD控制台，仅按本树地址关闭CSR_EUD_EN，再单次bootloader重启；关闭EUD时SSH reset后检查实际fastboot，不能重复未知切换。181前置JSON捕获。180声音原始report错标签176，boot-ID/runtime180与#180 guard证明实际180，派生标签更正、算法/原录音保留；181标签正确。

回退及边界见NEXT/WORKING-BOUNDARIES。180有72/6，176有178 SSR缺陷，175有reset超时；172/171 SD1原件保持，164/168是SD0。NV/校准/私人数据、电池保护和蓝牙/振动边界保持。显示/GPU及177 USB/Wi-Fi独立问题保留。
'''
for name,text,limit in [('NEXT-SESSION.md',next_text,6500),('AUDIO-NEXT-SESSION-PROMPT.txt',audio_text,4000)]:
    path=root/name
    saved=out/(name+'-before181-private')
    assert len(text.encode())<=limit,(name,len(text.encode()))
    if saved.exists():
        assert path.read_bytes()==saved.read_bytes() or path.read_text(encoding='utf-8')==text
    else:
        saved.write_bytes(path.read_bytes())
    path.write_text(text,encoding='utf-8',newline='\n')
status=root/'linux-port/docs/HARDWARE-STATUS.md'
saved=out/'HARDWARE-STATUS-before181-private.md'
assert not saved.exists();saved.write_bytes(status.read_bytes())
s=status.read_text(encoding='utf-8')
a=s.index('用途：');b=s.index('\n\n',a)
s=s[:a]+'''用途：当前硬件验收清单。最后核对：2026-10-14，kernel181/logdump181已部署，boot/DTB172、software/modules132/Mesa149/UCM173保持。初启动及一次受控ADSP停启通过，恢复后原生/桌面左右声学通过；完整音频goal active，实物耳机/自动crash/长PM/跨启动/音质保护仍开放。显示证据165/GPU149保持。以[181](../../reference/kernel181/README.md)、[180已保留失败](../../reference/kernel180/README.md)、[178](../../reference/kernel178/README.md)、[171人工听音](../../reference/kernel171/README.md)为准，规则见[边界](../../WORKING-BOUNDARIES.md)。'''+s[b:]
lines=s.splitlines()
for i,line in enumerate(lines):
    if line.startswith('| 音频 |'):
        lines[i]='''| 音频 | 171人工滴声；181 PDR/父IRQ/离线IRQ清理已部署，初启动及一次实际ADSP offline→running通过，资源回收/2旧FD EIO/自动HiFi和录音恢复；原生左右0.9574/0.9327、桌面0.9575/0.9942检出，893秒taint0、当前从0秒起ring所列20项0，PCM关、功放13/13静音、16保存控件恢复、main cache-only=N | 耳机/耳麦/按钮、自动crash/活跃流/长PM和跨启动、音质/瞬态/保护仍开放，用户暂无耳机。178 IRQ27720/config144/mask12/ASoC6/PDR2及启动PDR3/config8/mask1，180 config72/mask6真实失败保留，不被181一次通过覆盖 |'''
status.write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
print('CURRENT_DOCS_UPDATED_TO181')
