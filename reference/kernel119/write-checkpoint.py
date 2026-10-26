from pathlib import Path
import json
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel119'
runtime=json.loads((ref/'first-runtime-validation.json').read_text())
health=json.loads((ref/'current-health-validation.json').read_text())
pixel=json.loads((ref/'pixel-result-validation.json').read_text())
assert runtime['new_boot_verified'] and health['phosh_phoc_running'] and not pixel['graphics_acceptance']
session='sessions/119-k118-deployment-and-real-gpu-pixel-failure.md'
summary='阶段119已只刷logdump部署#118，boot/DTB/764模块及userdata保持。新启动自动恢复DRM/card1、Phosh/Phoc和FD640，0 CTL reset失败/0 KMS bind失败/0 RCU stall、taint0；启动DPU2次超时，300秒空闲窗口0新增，最后CRTC停用，不能代表持续绘制。签名glmark2非root真实像素验证33项仅2成功/25失败/6未知，退出0后发生1次CCU READ TRANSLATION GPU fault，2.2MiB devcoredump已私有保存；桌面进程仍存活、taint0，GPU功能验收失败。NV6/source4/vendor/persist/GPT及音频空闲保持，goal继续active。'
text=f'''# 阶段119：部署#118与真实GPU像素失败

2026-10-12。完整系统goal active，无人值守；本轮有实际部署、正常启动证据及更强GPU反例。

{summary}

## 本次启动守卫及部署

当前115第三启动重新检查：preflash完整成员hash、GPT六LUN的geometry/head/tail共18项、NV6/source4/vendor、persist及boot/logdump保持。当前完整分区hash与私有115回退镜像逐字节一致，复制其相同字节到119作为本轮回退，不重复读取168MiB大文件。档案b59460a09c1764cd49b94f840e041242219ebf2975539d1cbf4c6efd6dadcf73。

第一排空已停greetd/用户会话，但发现退出Phoc后内核fbcon恢复输出：msmdrmfb、无用户DRM客户端、plane allocated by fbcon、CRTC active1。守卫拒绝，不忽略。按[上游fb-helper语义](https://raw.githubusercontent.com/torvalds/linux/master/drivers/gpu/drm/drm_fb_helper.c)，确认本机fb0/driver后一次20秒有界blank=4，CRTC均active0，taint0。第二新prefix继续排空，PCM closed/双功放off muted1、ADSP/MPSS/SLPI均offline，NV/source/vendor保持；失败第一轮和fbcon前后日志并入第二归档3eaf50d8bdc1e4a25800432b3f980a7a70357f66f23e3ebef6d2c720aab57c79。

首次冻结成功后WSL缺usbmon，eud-usb-step在发送前打开usbmon失败，源码确认无OUT提交/F1；立即同boot受控fsfreeze -u，仍全排空。主机debugfs/usbmon检查与keepalive改到冻结之前，保留失败文件，新prefix ctl-final-read-retry1重新冻结。F1恰好90 02一次OUT，F1回执明确；之后Errno5是USB重枚举，reader/owner释放。独立fastboot身份、msmnile和boot100663296/logdump67108864检查通过，只flash logdump并reboot；没有boot、GPT、NV、persist写入或erase。

118 Image57a375cac03605f4d91099ca9994e234ef9dcd043564e1adbc66b4df3ccfa2ab；logdump14cdd1c47d43afe302cb1557de9573f2b96b2816c01116cb2bb5b465d68373a9；boot仍e9863902b2e9cd0cb02257f87d868989d69f613c66fbca3b6a7158a86b9c336f。模块/DTB兼容见118完整核验，不重装早期错误IPA包。

## 新启动实际状态

SSH有界240秒观察恢复#118；45秒EUD读取无发帧，完整native归档{runtime['native_archive_sha256']}。正常msm初始化minor1，IPA setup成功、taint0、CTL reset/KMS bind/RCU stall均0。本轮增加fbcon停止与最终read修正，不能把改善只归因一个变量。启动frame done timeout2次，Phoc后来一次Atomic commit EBUSY保留。相较115失败bind后人工式runtime rebind，这次不执行panel reprobe、不清greetd marker、不重启桌面，既有initial_session自动进入Phosh/Phoc。

首个native捕获较早，Phosh/Phoc/zram尚未出现；固定card0字段也不适用，因为本次主显示为card1，by-path/platform-ae01000.display-controller-card指向它。记录这两个测量边界，不将早期空字段当最终失败，不新增猜测WLR_DRM_DEVICES配置。最终collector从本机物理by-path解析card/minor。

启动display/radio traces保存后关闭，归档{runtime['trace_archive_sha256']}。300秒/10采样归档{health['archive_sha256']}：Phosh3492/Phoc3190仍运行，最新GL renderer FD640，connected/taint0、窗口DPU0/GPU0，NV/source/vendor/persist/GPT保持，PCM closed/功放off mute、SLPI offline/供电0、ADSP/MPSSrunning，Wi-Fi up、zram约10GiB/priority300、MM sim-missing。收尾DRM客户端仍Phoc、但两CRTC inactive；只能证明空闲状态，不能宣称持续scanout/GPU压力通过。RTC早期时间跳变由后续网络时间校正，hwclock/IIO失败仍开放。

## 真正绘制验证揭示未完成项

从[Alpine官方aarch64包](https://pkgs.alpinelinux.org/contents?arch=aarch64&branch=edge&name=glmark2&repo=testing)取得glmark2-2023.01-r1，APK签名完整验证。初版apk fetch带版本matcher失败、URL重定向为空、apk extract --help返回1均保留；改已观察官方URL直接下载并签名核验、补归档。未安装/升级系统包，world/installed前后hash一致。解包到/tmp/k119-glmark2，UID10000运行，30秒wall/25秒CPU/768MiB地址空间限制，--off-screen --validate，数据路径私有解包目录；没有截图、人眼或声音判断。

实际freedreno/FD640/OpenGL ES3.2 Mesa26.2.4。默认33场景2 Success（bump normals/height）、25 Failure、6 Unknown；退出码0并非成功。真实SurfaceSize1080x2259而非默认800x600，版本2023.01可能存在Wayland resize/FBO/validation行为问题，参考[上游resize问题248](https://github.com/glmark2/glmark2/issues/248)与[上游canvas实现](https://raw.githubusercontent.com/glmark2/glmark2/2023.01/src/canvas-generic.cpp)。这只是需排除的测试工具因素，不解释或忽略内核GPU fault。

测试退出约1092.89s后，1094.04s出现CCU READ TRANSLATION/IOMMU GPU fault，ring0 fence报错。立即停止额外负载、无手动reset/replay/删除coredump。之后完整native归档{pixel['post_fault_archive_sha256']}，仍Phosh/Phoc原PID/taint0、DPU累计2/GPU累计1、音频空闲、来源/NV与包数据库保持。devcd2 2317218字节，SHA2565f6399437cb255c9e78cd53395133993b7016fdc999a174db4e60951eadccc6a，header owner glmark2；原始GPU BO/寄存器/画面数据保持私有。初次绘制归档{pixel['test_archive_sha256']}，签名来源归档{pixel['source_archive_sha256']}，全成员hash核对通过。

下一步按[Mesa官方Freedreno调试文档](https://docs.mesa3d.org/drivers/freedreno.html)离线crashdec解coredump，定位CCU/ring/IB命令和无效IOVA；可读工具/驱动固定版本源码，必要时离线反汇编同机SQE固件，不上传原始dump。先修正或隔离glmark2旧Wayland resize/FBO因素；不连续重跑33场景、不设置全桌面FD_MESA_DEBUG隐蔽绕过、不用软件渲染冒充GPU修复。若这一错误长期难解，完整留档后转CCI/CAMCC/摄像头SoC资源或其它未完成项。

## 剩余范围与后续守卫

当前已部署kernel118，不是115；回退/下一正常reboot必须新boot的完整GUI/fbcon/音频/无线/远程处理器排空、sync/fsfreeze与F1回执，不用119部署前115守卫。当前boot guard在私有kernel119/current-boot-id-private.txt和手机k119-first-runtime。当前GPU fault1但taint0，不能用taint0表示GPU稳定。

rootfs115 fixed 936包/764模块完整镜像d8fc01cea0187b5f1174a910dc01f4f566714716a78debf6061af37d1dd3f1f4仍兼容118，未全量刷userdata；离线CAMSS116未部署。完整传感器、camera、GNSS fix、蜂窝数据/通话、指纹、充电、休眠/长稳等15组继续开放。主机C约2.4GiB，build118在E盘20GiB ext4文件，需ensure挂载后读源码，不能再向C clone大树；本轮没有恢复遗留手工检查，也没有对外消息/呼叫/文档push。
'''
(root/session).write_text(text)
for name in ['README.md','FLYWHEEL.md']:
    p=root/name;t=p.read_text();marker='[阶段118](sessions/118-final-reset-read-build-and-host-space-recovery.md)'
    t=t.replace(marker,f'[阶段119]({session})，'+marker,1)
    old=t.split('\n\n')[2];assert old.startswith('阶段118');p.write_text(t.replace(old,summary,1))
p=root/'DOCS-INDEX.md';t=p.read_text().replace('当前：[阶段118]',f'当前：[阶段119]({session})、[阶段118]',1)
t=t.replace('| sessions/118-',f'| {session}、reference/kernel119/ | 新boot部署118/自动桌面、300秒idle边界、真实GPU25项像素失败及CCU迟发fault/coredump |\n| sessions/118-',1);p.write_text(t)
p=root/'linux-port/docs/HARDWARE-STATUS.md';t=p.read_text().replace('，阶段118）','，阶段119）',1)
t=t.replace('[阶段118]',f'[阶段119](../../{session})、[阶段118]',1);old=t.split('\n\n')[3];assert old.startswith('阶段118');t=t.replace(old,summary,1)
rows={
'原生显示面板':('新#118正常boot自动DRM/card1/Phosh；CTL reset/KMS bind/RCU失败0，启动DPU2；300秒idle0新增、最终CRTC inactive','继续持续绘制/命令帧/休眠验收；单次boot不能认定永久修复'),
'GPU':('FD640/ES3.2 Mesa26.2.4；真实像素33项2成功25失败6未知，迟发CCU GPU fault1；原桌面PID存活/taint0，coredump私有','离线crashdec/SQE/无效IOVA及旧glmark Wayland resize/FBO因素；不可因exit0/taint0认定通过'),
'普通USB与OTG':('当前#118 NCM/SSH/SCP可达；冻结F1回执/只flash logdump/native回读通过，首次usbmon缺失安全thaw后修正','OTG/USB3/休眠/长稳；保留物理by-path及host usbmon前置检查'),
'Wi-Fi':('当前#118 2.4GHz NetworkManager自动连接/up，官方APK HTTPS下载通过','5GHz有界失败待修；冷启动/休眠/长稳'),
'音频':('本机UCM/扬声器/DMIC0历史电气验收保留；当前#118 ADSP/card0运行，GPU测试后PCM closed双功放静音','自动音频回归；实际声音质量/耳机/DSM/校准/休眠未验收'),
'蜂窝网络/数据':('当前#118本机IPA v4.1/固件初始化、rmnet_ipa0，TX delay0 WARN；MM sim-missing，NV6/source4保持','移动数据/通话未验收，参考clock/ICC待压力；SSR/冷启动/休眠/长稳')}
lines=t.splitlines()
for i,line in enumerate(lines):
    for name,(state,next_work) in rows.items():
        if line.startswith(f'| {name} |'):lines[i]=f'| {name} | {state} | {next_work} |'
p.write_text('\n'.join(lines)+'\n')
(root/'NEXT-SESSION.md').write_text(f'''# 继续检查点：阶段119（2026-10-12）

完整系统goal active。上一轮实际部署正常boot及GPU反例均为progress。继续无人值守；不要求画面/触摸/听音，不发送消息/呼叫，长难项留档后转项。

先读[阶段119]({session})、[118构建](sessions/118-final-reset-read-build-and-host-space-recovery.md)、[117](sessions/117-parser-boundaries-and-same-boot-desktop-recovery.md)、[116](sessions/116-camss-foundation-and-own-sensor-binaries.md)、[15组](linux-port/docs/HARDWARE-STATUS.md)。当前证据reference/kernel119/first-runtime-validation.json、current-health-validation.json、pixel-result-validation.json。

{summary}

当前root/kernel：#118 SMP PREEMPT/7.3.0-rc6-rmx1931-samurai+。DRM本机by-path/platform-ae01000.display-controller-card -> card1，renderD128；不要固定card0。Phosh3492/Phoc3190原PID仍运行，greetd既有initial_session自动进入，本次没有panel reprobe/marker reset。初始采样没赶上GUI/zram，随后均自动启动。空闲300秒收尾CRTC均inactive，不能表示GPU/显示压力通过。

真实glmark2非root--off-screen --validate失败：33项2success/25failure/6unknown，exit0；FD640/ES3.2/Mesa26.2.4；Surface1080x2259有旧工具resize/FBO疑点。迟发CCU READ TRANSLATION GPU fault1，2.2MiB devcd2完整private。原始归档E:/edk2-samurai-out/kernel119/post-pixel-fault-private.tar.gz，抽取gpu-coredump/devcd2-private.data，hash5f6399437cb255c9e78cd53395133993b7016fdc999a174db4e60951eadccc6a。按Mesa官方Freedreno文档离线crashdec，读固定源码/SQE反汇编；不要重跑重负载/replay/手动reset或全桌面debug参数。CPU/GPU shader缓存少量改变，APK world/installed未改；签名tool只解包/tmp/k119-glmark2，未系统安装。

当前健康：taint0不等于GPU稳定；DPU累计2/GPU累计1。SLPI offline、sensor-power vdd/vddio0、原selector00121保持。PCM closed/双功放powered0 muted1，ADSP/MPSSrunning；Wi-Fi2.4GHz up、postmarketos-zram-swap已start/~10GiB/priority300、MM sim-missing。display/radio trace已保存并关闭，未清原证据。NV6/source4/vendor/persist/GPT均通过。RTC/NTP启动时钟跳变、hwclock/IIO失败仍开放。

118源在E盘私有20GiB ext4文件E:/edk2-samurai-out/kernel118/build-volume.ext4，挂载/home/cy122/pmos-samurai-kernel118，先reference/kernel118/ensure-build-volume.py再读；闲置WSL会卸载。C仅约2.4GiB，禁止向C复制大kernel/Mesa树或扩大原VHD。115/116在原WSL，源/镜像baseline保持。118仅DPU最终读小修正，DTB和全部764模块内容兼容115、CPIO成员语义相同、CONFIG_MODVERSIONS关闭。116 CAMSS/media不合入。

118已部署logdump14cdd1c47d43afe302cb1557de9573f2b96b2816c01116cb2bb5b465d68373a9；boot仍115 e9863902b2e9cd0cb02257f87d868989d69f613c66fbca3b6a7158a86b9c336f。115完整回退E:/edk2-samurai-out/kernel119/boot-partition-before.img和logdump-before.img，后者fcb1b5380e664a49abf7d6098863d23683f70be4c1d1d144df5a8dd356e46e2e。任何回退/下一reboot重新取得当前118身份和GUI/fbcon/音频/无线/remoteproc全排空+sync/freeze/F1证明，不能套119的部署前115 guard。当前boot guard私有kernel119/current-boot-id-private.txt及手机/var/lib/samurai/k119-first-runtime/boot-id-private.txt。停止Phoc后fbcon可能复活active1，需要确认nativeowner后有界blank=4，而非绕过CRTC guard。host debugfs/usbmon前置准备，F1一次90 02+回执之后的USB Errno5可以是重枚举。

rootfs115 fixed镜像E:/edk2-samurai-out/kernel115/samurai-rootfs-f2fs-delay-fixed.simg，1,817,970,276字节、展开119033245696、SHA d8fc01cea0187b5f1174a910dc01f4f566714716a78debf6061af37d1dd3f1f4；936包/764模块、own IPA固件/zram/elogind已校验，仍兼容118，未全量刷。旧初版115 module包包含IPA delay修正前版本，不得回装；runtime stripped IPA bdd85687f4889cfe78ca7dbcd8974618fc1a523d65b4d3678f6800a42ceb2ce0。

摄像头：116 CAMSS基础/v1.1隔离build通过未部署；本机五sensor.so/六sensormodule BIN只读+hash通过。BIN1.3.2与工具2.0.0/XSD有界解析失败0XML，已留档转项，不猜寄存器。Hotdog固定47087509c4289c2580c54f5433e55366b2e00445，0056 CAMSS/0057 CCI SoC DT已读，下一可继续CCI/CAMCC/C-PHY/DMA/ICC/QoS与本机19781资源。GPU难题若长卡则先记录转这些项。

所有身份/固件/原始日志/dump/源镜像私有，不上传dump、不push文档、不用erase userdata脚本。Windows静态USB IP因admin被拒已修正false-success，APIPA/16 SSH可达；不改安全设置。生成脚本属于一次性阶段工具，勿重跑prepare-tools.py覆盖手工增加的fbcon/usbmon/第二prefix守卫。
''')
print('CHECKPOINT119_DEPLOYED118_AND_GPU_FAILURE_DOCUMENTED_WITH_15_GROUPS')
