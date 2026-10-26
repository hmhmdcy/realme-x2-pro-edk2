# 阶段119：部署#118与真实GPU像素失败

2026-10-12。完整系统goal active，无人值守；本轮有实际部署、正常启动证据及更强GPU反例。

阶段119已只刷logdump部署#118，boot/DTB/764模块及userdata保持。新启动自动恢复DRM/card1、Phosh/Phoc和FD640，0 CTL reset失败/0 KMS bind失败/0 RCU stall、taint0；启动DPU2次超时，300秒空闲窗口0新增，最后CRTC停用，不能代表持续绘制。签名glmark2非root真实像素验证33项仅2成功/25失败/6未知，退出0后发生1次CCU READ TRANSLATION GPU fault，2.2MiB devcoredump已私有保存；桌面进程仍存活、taint0，GPU功能验收失败。NV6/source4/vendor/persist/GPT及音频空闲保持，goal继续active。

## 本次启动守卫及部署

当前115第三启动重新检查：preflash完整成员hash、GPT六LUN的geometry/head/tail共18项、NV6/source4/vendor、persist及boot/logdump保持。当前完整分区hash与私有115回退镜像逐字节一致，复制其相同字节到119作为本轮回退，不重复读取168MiB大文件。档案b59460a09c1764cd49b94f840e041242219ebf2975539d1cbf4c6efd6dadcf73。

第一排空已停greetd/用户会话，但发现退出Phoc后内核fbcon恢复输出：msmdrmfb、无用户DRM客户端、plane allocated by fbcon、CRTC active1。守卫拒绝，不忽略。按[上游fb-helper语义](https://raw.githubusercontent.com/torvalds/linux/master/drivers/gpu/drm/drm_fb_helper.c)，确认本机fb0/driver后一次20秒有界blank=4，CRTC均active0，taint0。第二新prefix继续排空，PCM closed/双功放off muted1、ADSP/MPSS/SLPI均offline，NV/source/vendor保持；失败第一轮和fbcon前后日志并入第二归档3eaf50d8bdc1e4a25800432b3f980a7a70357f66f23e3ebef6d2c720aab57c79。

首次冻结成功后WSL缺usbmon，eud-usb-step在发送前打开usbmon失败，源码确认无OUT提交/F1；立即同boot受控fsfreeze -u，仍全排空。主机debugfs/usbmon检查与keepalive改到冻结之前，保留失败文件，新prefix ctl-final-read-retry1重新冻结。F1恰好90 02一次OUT，F1回执明确；之后Errno5是USB重枚举，reader/owner释放。独立fastboot身份、msmnile和boot100663296/logdump67108864检查通过，只flash logdump并reboot；没有boot、GPT、NV、persist写入或erase。

118 Image57a375cac03605f4d91099ca9994e234ef9dcd043564e1adbc66b4df3ccfa2ab；logdump14cdd1c47d43afe302cb1557de9573f2b96b2816c01116cb2bb5b465d68373a9；boot仍e9863902b2e9cd0cb02257f87d868989d69f613c66fbca3b6a7158a86b9c336f。模块/DTB兼容见118完整核验，不重装早期错误IPA包。

## 新启动实际状态

SSH有界240秒观察恢复#118；45秒EUD读取无发帧，完整native归档32e1078a66d5d78d65e384cff6dbe6bb44f544064582814998c7a580ea33d36b。正常msm初始化minor1，IPA setup成功、taint0、CTL reset/KMS bind/RCU stall均0。本轮增加fbcon停止与最终read修正，不能把改善只归因一个变量。启动frame done timeout2次，Phoc后来一次Atomic commit EBUSY保留。相较115失败bind后人工式runtime rebind，这次不执行panel reprobe、不清greetd marker、不重启桌面，既有initial_session自动进入Phosh/Phoc。

首个native捕获较早，Phosh/Phoc/zram尚未出现；固定card0字段也不适用，因为本次主显示为card1，by-path/platform-ae01000.display-controller-card指向它。记录这两个测量边界，不将早期空字段当最终失败，不新增猜测WLR_DRM_DEVICES配置。最终collector从本机物理by-path解析card/minor。

启动display/radio traces保存后关闭，归档93882196ede6483798fde925a4c565cfbcd67a7e0bba1dbc981a36da0af4cbf2。300秒/10采样归档b1fc4eb57404c9965f74ef036be270bfc8c480fa2428708db13a45ef0f65ff9c：Phosh3492/Phoc3190仍运行，最新GL renderer FD640，connected/taint0、窗口DPU0/GPU0，NV/source/vendor/persist/GPT保持，PCM closed/功放off mute、SLPI offline/供电0、ADSP/MPSSrunning，Wi-Fi up、zram约10GiB/priority300、MM sim-missing。收尾DRM客户端仍Phoc、但两CRTC inactive；只能证明空闲状态，不能宣称持续scanout/GPU压力通过。RTC早期时间跳变由后续网络时间校正，hwclock/IIO失败仍开放。

## 真正绘制验证揭示未完成项

从[Alpine官方aarch64包](https://pkgs.alpinelinux.org/contents?arch=aarch64&branch=edge&name=glmark2&repo=testing)取得glmark2-2023.01-r1，APK签名完整验证。初版apk fetch带版本matcher失败、URL重定向为空、apk extract --help返回1均保留；改已观察官方URL直接下载并签名核验、补归档。未安装/升级系统包，world/installed前后hash一致。解包到/tmp/k119-glmark2，UID10000运行，30秒wall/25秒CPU/768MiB地址空间限制，--off-screen --validate，数据路径私有解包目录；没有截图、人眼或声音判断。

实际freedreno/FD640/OpenGL ES3.2 Mesa26.2.4。默认33场景2 Success（bump normals/height）、25 Failure、6 Unknown；退出码0并非成功。真实SurfaceSize1080x2259而非默认800x600，版本2023.01可能存在Wayland resize/FBO/validation行为问题，参考[上游resize问题248](https://github.com/glmark2/glmark2/issues/248)与[上游canvas实现](https://raw.githubusercontent.com/glmark2/glmark2/2023.01/src/canvas-generic.cpp)。这只是需排除的测试工具因素，不解释或忽略内核GPU fault。

测试退出约1092.89s后，1094.04s出现CCU READ TRANSLATION/IOMMU GPU fault，ring0 fence报错。立即停止额外负载、无手动reset/replay/删除coredump。之后完整native归档1b1aaa5138818d3499966352fe826f934268d45e2b8b8aedfb59906c1d9620f5，仍Phosh/Phoc原PID/taint0、DPU累计2/GPU累计1、音频空闲、来源/NV与包数据库保持。devcd2 2317218字节，SHA2565f6399437cb255c9e78cd53395133993b7016fdc999a174db4e60951eadccc6a，header owner glmark2；原始GPU BO/寄存器/画面数据保持私有。初次绘制归档7eb66772c4b3eed32b1d9e580414e222717fd85dfbbbb40cf525923c141ae7a2，签名来源归档2893d2f399331265c3b64b8c66d5062428c09df158b51cb459b7dfee8ce012fb，全成员hash核对通过。

下一步按[Mesa官方Freedreno调试文档](https://docs.mesa3d.org/drivers/freedreno.html)离线crashdec解coredump，定位CCU/ring/IB命令和无效IOVA；可读工具/驱动固定版本源码，必要时离线反汇编同机SQE固件，不上传原始dump。先修正或隔离glmark2旧Wayland resize/FBO因素；不连续重跑33场景、不设置全桌面FD_MESA_DEBUG隐蔽绕过、不用软件渲染冒充GPU修复。若这一错误长期难解，完整留档后转CCI/CAMCC/摄像头SoC资源或其它未完成项。

## 剩余范围与后续守卫

当前已部署kernel118，不是115；回退/下一正常reboot必须新boot的完整GUI/fbcon/音频/无线/远程处理器排空、sync/fsfreeze与F1回执，不用119部署前115守卫。当前boot guard在私有kernel119/current-boot-id-private.txt和手机k119-first-runtime。当前GPU fault1但taint0，不能用taint0表示GPU稳定。

rootfs115 fixed 936包/764模块完整镜像d8fc01cea0187b5f1174a910dc01f4f566714716a78debf6061af37d1dd3f1f4仍兼容118，未全量刷userdata；离线CAMSS116未部署。完整传感器、camera、GNSS fix、蜂窝数据/通话、指纹、充电、休眠/长稳等15组继续开放。主机C约2.4GiB，build118在E盘20GiB ext4文件，需ensure挂载后读源码，不能再向C clone大树；本轮没有恢复遗留手工检查，也没有对外消息/呼叫/文档push。

## 离线Mesa解码完成，保留根因边界

上游同版本两份真实fixture（crash、crash_prefetch）在有界CPU离线运行中exit0，stdout与发布源码的reference逐字节相同，SHA256均一致，验证记录crashdec-fixtures-validation.json。保留每项stderr90字节，不删除诊断输出。

[官方Mesa 26.2.4归档](https://archive.mesa3d.org/mesa-26.2.4.tar.xz)通过HTTPS下载，SHA256 bce5f7fbebb934373b86c999a064d52fb5065878dc57f287f95346648ec832e9；未声称GPG签名认证。源码解压到118的E盘ext4隔离卷mesa-offline，版本文件26.2.4。初次tar路径守卫不接受顶层目录无斜杠，未解压；修正为Path.parts首段精确匹配及无父路径，data过滤后解压。WSL闲置卸载导致第一次挂载守卫拒绝，fetch/build/decode均增加同进程ensure-build-volume。电脑Ubuntu官方源新增Meson/Ninja/pkg-config/Mako/XML/DRM/Lua/archive开发依赖，约30MiB安装，不改手机APK。

初次配置缺Lua，虽Meson返回0但没有crashdec目标；保留日志，补依赖后clearcache/reconfigure成功。一次构建提前于配置完成，Meson锁拒绝，未绕过锁；等待配置进程退出后继续。只请求src/freedreno/decode/crashdec及其依赖272目标，不编译/部署Mesa图形驱动，不执行replay。原始编译警告保留。x86_64解码器SHA256 4a68706bad1d03366196327dd0ebf2294910fd73fad93fdbabdf19d43d2c4b3b，私有副本gpu-coredump/crashdec-mesa26.2.4-x86_64。

私有devcd2原hash先核验；crashdec -s -f、RNN_PATH指定同版本寄存器XML，CPU40秒/墙钟50秒/地址空间1GiB/文件32MiB/无自身core限制。实际3.12秒、exit0、输出4293117字节、无缺失寄存器数据库，找到ESTIMATED CRASH LOCATION；完整输出只在gpu-coredump/decoded-summary-private.txt，SHA256 804bca705bad979d2905d39ec84c17f4507517aa8692ac2259850cb6ed5ac2d2。解码不接触手机，不上传dump。

转储comm精确glmark2，fault READ/TRANSLATION/CCU；fault-info与pgtable-fault-info TTBR一致。51个BO中没有包含fault IOVA，最近BO边界相距36864/40960字节，四级页表描述符有1个0。估算停止前CP_WAIT_FOR_ME、CP_SET_MODE，后CP_SET_BIN_DATA5、CP_SET_VISIBILITY_OVERRIDE。没有vm-log历史，不能证明use-after-free/错误buffer基址/CCU cache状态哪项是原因。当前内核msm_gpu.c crashstate_get_bos的非VM_BIND分支只枚举submit->bos，VM_BIND分支枚举VM映射；BO列表不是完整地址空间的无条件证明。Mesa文档明确流水线导致停止位置可能晚于触发状态，不能直接修改CP_SET_BIN_DATA5。mapping-analysis.json公开只保留计数/相对边界/命令名称，不公开地址或shader/raw buffers。

后续优先继续旧glmark resize/FBO静态复现及RB/CCU render-target映射分析，再设计小负载的单场景验收；禁止重跑整套33负载、重放或全桌面debug开关。此轮GPU离线分析已得到边界，暂转摄像头CCI/CAMCC/C-PHY/DMA/ICC资源核对，符合长難项留档后换项。最终SSH复核#118/taint0/Phosh3492/Phoc3190/DPU2/GPU1/PCM双closed/SLPI offline，无追加GPU故障。
