"""Finalize stage265 documentation from verified receipts."""
from pathlib import Path
import json,re
R=Path(__file__).parent;repo=R.parents[1]
d=json.loads((R/'production-validation.json').read_text());e=json.loads((R/'evidence-validation.json').read_text())
assert d['production']['total_checks']==2972 and d['candidate']['total_checks']==3201 and e['files_verified']==924
p=R/'README.md';s=p.read_text().replace('# 265 相机连续拍照与共享缓冲退役检查（进行中）','# 265 公共相机缓冲退役修复与系统部署')
assert '## 最终组合与验收' not in s,'Documentation checkpoint already finalized'
s=s.replace('部署后验收进行中。','部署后2972次保留前缀检查与实际窗口快门已通过。')
s=s.replace('下一步核对实际Busy所有权与图像内存身份，并验证两个生命周期窗口的组合修复。当前失败候选仅临时加载，续作结束前应恢复正常系统WP或经充分验收后原生部署。','后续组合验收已通过；这里保留单项失败，不能把单独修改当作充分修复。私人覆盖已撤。')
mark=s.index('\n\n后摄IMX319')
success='''
## 最终组合与验收

退役时，普通PW引用可能先于最后一个Gst引用归还；新增Busy引用及独立元数据映射保留这部分所有权。SPA在图重新绑定时使用新图像分配，使旧fd保留旧内存。两项共同覆盖退役窗口，不逐帧复制像素或清零计数。映射查询支持没有默认映射的真实导入块。传感器方向/裁剪仍应在内核层补齐，本阶段未改内核或刷写。

| 组件 | 版本 | ELF SHA256前缀 |
| --- | --- | --- |
| pipewire-libs | 1.6.9-r3 | e946e5115db5 |
| pipewire-spa-libcamera | 1.6.9-r3 | 3529ac3cf6f5 |
| gst-plugin-pipewire | 1.6.9-r3 | 2f893caf55ac |

[汇总](production-validation.json)：

- 组合候选run12—14及6000141—143：3201次保留检查、前后摄9张照片，六轮关闭、崩溃恢复与原生并用，0内容/PTS变化和回收错误。
- 系统路径run16—17及6000151—154：2972次保留检查、前后摄6张照片，六轮关闭、崩溃/跨框架并用、1.2秒全池保留后恢复，0变化/回收错误。共享缓冲池开启，无应用复制开关或私人库覆盖。
- 实际Snapshot前摄窗口：777个新缓冲、766次渲染、PTS连续13.473447秒，0回收/总线错误，正常quit/退出0。观察到的win.take-picture动作保存1920×1080 JPEG，1,548,898字节，完整解码通过。[窗口](snapshot-gui-validation.json)、[渲染](snapshot-flow-validation.json)、[解码](snapshot-photo-0-validation.json)。
- 控制器未找到所匹配的切换动作，GUI前后切换尚未验收，不能据此断言应用无此功能。
- 保留检查仅哈希每帧前65536字节，并非整帧不变证明。诊断确认实际持有Busy引用且无缺失；各轮72个图像内存inode不同。[系统后摄](ownership-16-validation.json)、[系统前摄](ownership-17-validation.json)。

光学画质不因流稳定或JPEG可解码而自动验收。

## 失败与修正过程
'''
s=s[:mark]+'\n'+success+s[mark:]
s=s.replace('待办：候选实机连续拍照与前后摄回归、系统原生包部署与回退验证；驱动方向/裁剪元数据、后摄低照度与颜色、GUI切换、录像/长稳和其它后摄。相机适配目标保持active。','待办：内核方向/旋转/裁剪元数据、后摄低照度与颜色、GUI选择/切换、录像/长稳和S5K3M5/GW1等后摄。既有CPU显示配置保留，默认GPU及GPU ISP退出告警未修；完整相机适配目标保持active。')
s+='''
## 包、源码和最终状态

[包与ABI](package-build-validation.json)、[升级模拟](package-simulation-validation.json)、[安装](package-install-validation.json)：三个APK使用已有可信密钥，SPA/Gst均精确依赖core-r3。只替换三个ELF，其余42个普通文件和一个符号链接保持；只改变三个包记录，仍961包。手机/PC保留原core/SPA r2与Gst r1，六包验签及三包联合降级模拟通过。

APK3解包工具在空目录拒绝共享父目录。最终从可信上游载荷与保留的当前ELF重建基线，逐项匹配当前签名APK3的完整SHA256文件表，再替换三个组件签名。构建器为build-final-packages.py；工具和生成器失败保留在私人日志。旧准备脚本/SDK目录是一发式历史上下文，不盲目重跑。

[完整固定配方](../../linux-port/packages/pipewire-common/README.md)通过12项SHA512、7个补丁零fuzz应用、shell语法及7个编译输入精确匹配。[源码核验](recipe-prepare-validation.json)。实际为SDK增量编译及可信载荷打包，完整abuild、全新rootfs和跨启动尚未执行。旧broadcast树的SPA被失败实验改写过，按当前配方复现。

[最终健康](final-health-validation.json)：49项框架/配置/启动项验证，33个上下文全终态，PM休眠、MCLK关闭、图案/翻转0、trace清理，新增WARN/Oops/GPU/fatal等均0、taint0。所有部署后测试与GUI共用最终标准服务。

[私人归档](evidence-validation.json)：924个文件逐项SHA256验证，37,809,506字节，SHA256为fd103917a3e211f23f2a88011e7b908e805e9f607a606d7ef35232feb6b44586。严格原密钥USB传输中断后，已核对12MiB前缀并续传，归档和全部成员通过。图片与构建资料留在E:/edk2-samurai-out/kernel265，不进入文档镜像。
'''
p.write_text(s)
recipe='''# PipeWire公共相机缓冲修复配方

PipeWire1.6.9-r3，基于Alpine aports固定提交0afac626498565714f7a06c04589112584cc95f4的完整官方APKBUILD与辅助文件。归档固定GitHub1.6.9 tar的名称与摘要，详见[source-lock](source-lock.json)。

保留上游systemd补丁，并顺序追加六个项目补丁：

1. Gst延后unref的上游锁顺序修复。
2. 保留可选复制诊断功能，默认关闭；生产启动项不启用。
3. 核心可靠广播、远端代理重协商与绑定IO生命周期。
4. SPA Busy引用、延迟复用、IO初始化及图退役后的新图像分配。
5. 公共映射范围查询，支持没有默认映射的真实导入块。
6. Gst共享帧的独立Busy引用/元数据映射与所有权诊断。

SPA自动声明可靠广播，标准客户端共用修复。SPA与Gst子包均精确依赖同版本core；应用不需要复制开关或私人库路径。新增引用不逐帧复制像素或清零Busy计数。

精确原始tar的12项source SHA512、7个补丁零fuzz应用、shell语法及7个编译输入与部署源码一致。[核验](../../../reference/kernel265/recipe-prepare-validation.json)。**完整abuild尚未执行**；不能写成全部子包重建或全新rootfs通过。

实机为三个原生可信签名APK：SDK增量源码编译后保留当前可信载荷，完整文件表校验，其余42个普通文件与一个符号链接保持，替换三个ELF。仅三个包记录变化，仍961包；core/SPA r2与Gst r1的联合回退包保留并模拟通过。[包与ABI](../../../reference/kernel265/package-build-validation.json)、[事务](../../../reference/kernel265/package-install-validation.json)。

组合候选3201次、原生系统2972次保留前缀检查无内容/PTS变化或回收错误；原生前后摄6张照片及实际Snapshot前摄窗口快门通过。检查限定每帧前65536字节。单独Gst/SPA与旧临时引用候选的失败保留；画质、GUI切换、其它后摄、GPU和完整适配继续开放。[完整结果与限制](../../../reference/kernel265/README.md)。
'''
(repo/'linux-port/packages/pipewire-common/README.md').write_text(recipe)
p=repo/'NEXT-SESSION.md';old=p.read_text();tail=old[old.index('## 用户态维护与桌面'):]
prefix='''# Realme X2 Pro 当前检查点

265相机公共层：core/SPA/Gst 1.6.9-r3已原生部署，组合候选3201次、系统2972次保留前缀检查0变化/回收错误。系统前后摄6张照片、六轮关闭、崩溃/跨框架并用及全池恢复通过；Snapshot窗口777缓冲/766渲染、1920×1080 JPEG解码通过。后摄偏暗、内核元数据、GUI切换、其它后摄及GPU仍待办，目标active。[265结果与失败](reference/kernel265/README.md)、[源码配方](linux-port/packages/pipewire-common/README.md)。

先读[操作边界](WORKING-BOUNDARIES.md)、[硬件清单](linux-port/docs/HARDWARE-STATUS.md)和265。同260启动guard为/var/lib/samurai/k260-work/boot-id-private.txt，运输复用私人E:/edk2-samurai-out/kernel260/host.py的严格原主机密钥；旧启动身份不可用于切换。

## 相机当前部署与续作

核心e946e511…、SPA3529ac3c…、Gst2f893caf…系统路径已映射，SPA/Gst精确依赖core-r3。仅三个包记录变化、仍961包；原core/SPA r2与Gst r1可信APK在手机/PC保留，联合降级模拟通过。新增Gst Busy所有权＋SPA图退役后新图像分配，不复制像素或清零计数。boot235/Image183、libcamera r15/config-r10的49项、无复制开关与CPU显示配置保持。

当前PW8911/start4904567、WP8913/start4904568、Phosh2261/start1967；权威/var/lib/samurai/k265-services-current-private.json。私人覆盖已撤，264旧清单与265候选PID不可再用。33个上下文全终态、PM/MCLK/图案/trace恢复、新增fault0/taint0，924个归档成员SHA核验。手机k265与PC E:/edk2-samurai-out/kernel265保留原包、失败及私人图片，不重复一发式安装或快门。

检查限定每帧前65536字节。v2一次多客户端无结果未记退出码，临时引用竞争由64轮对照检出；v3单独1次变化、SPA单独4次变化，组合重新验收通过。完整配方12摘要/7patch/7输入匹配；实际为SDK增量编译与可信载荷打包，完整abuild未跑。旧SDK broadcast树SPA被失败实验改写过，按当前配方复现。

下一步先补内核方向/裁剪元数据、IMX319低照度，再GUI选择/切换、S5K3M5/GW1、颜色/噪声、录像与长稳。用户确认后摄朝向光线较弱的电脑桌，有细节而偏暗，不归因于遮挡。GUI控制器未匹配切换动作，本轮只验收前摄窗口。默认GPU/GPU ISP退出告警未修。图/格式/AE由libcamera正常管理，不外部写回旧值。

'''
tail=tail.replace('262—264相机修复','262—265相机修复').replace('archive/NEXT-SESSION-through263-2026-10-18.md','archive/NEXT-SESSION-through264-2026-10-18.md')
p.write_text(prefix+tail)
p=repo/'linux-port/docs/HARDWARE-STATUS.md';s=p.read_text()
s=re.sub(r'^264相机（2026-10-18）：.*$', '265相机（2026-10-18）：公共core/SPA/Gst 1.6.9-r3原生组合修复；同260启动/961包，boot235/Image183与r15/r10保持。系统2972次保留前缀检查0变化/回收错误，前后摄6张照片、六轮关闭、崩溃/并用/全池恢复通过；Snapshot前摄777缓冲/766渲染及1920×1080 JPEG解码。33个上下文全终态，PM/MCLK恢复、新增fault0/taint0。后摄低照度、内核元数据、GUI切换、其它后摄/录像及GPU仍待办。[265边界](../../reference/kernel265/README.md)、[源配方](../packages/pipewire-common/README.md)。',s,count=1,flags=re.M)
s=s.replace('264公共缓冲修复所测场景通过','265公共缓冲组合修复所测场景通过')
row='| 摄像头 | 265公共core/SPA/Gst 1.6.9-r3原生部署；系统2972次保留前65536字节检查0变化/回收错误，前后摄6张照片；六轮关闭、崩溃恢复、原生/Gst并用和1.2秒全池恢复通过；Snapshot前摄777缓冲/766渲染、1920×1080 JPEG解码；49项r15/r10保持，PM/MCLK恢复/新增fault0 | IMX319低照度偏暗但有细节；方向/旋转/裁剪内核接口、GUI切换和光学画质待验收；S5K3M5/GW1、录像/长稳、完整abuild/rootfs待完成；CPU显示回退保留，默认Vulkan/GPU ISP退出告警未修，Megapixels接入待办 |'
s,n=re.subn(r'^\| 摄像头 \|.*$',row,s,count=1,flags=re.M);assert n==1;p.write_text(s)
print(json.dumps(dict(stage=265,next_session_bytes=(repo/'NEXT-SESSION.md').stat().st_size,archive_264_preserved=True,documents_updated=True)))

