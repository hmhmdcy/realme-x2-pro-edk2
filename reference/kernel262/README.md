# 262：前摄保存 JPEG、缓冲持有复现与 CPU 复制路径

2026-10-18，接续 Linux 相机适配，目标仍 active、完整适配未完成。同260启动，boot235/Image183、libcamera r15/config-r10保持；本轮只升级 `gst-plugin-pipewire` 1.6.9-r0 → r1，包数仍961，没有重启或刷新内核。后续已通过正常接口解锁并验证实际Snapshot预览。用户明确要求通用相机兼容，逐应用复制仅作临时缓解，不能作为适配终点。

## 后续解锁、实际预览与通用修复方向

用户提示可以取消锁屏。核对发现 `lock-enabled=false` 和 `idle-delay=0` 本来已设置，无需再写配置；标准 `org.gnome.ScreenSaver.SetActive(false)` 返回成功，GetActive从true变为false。没有更改密码、PAM或认证设置。[解锁收据](lock-policy-validation.json)

随后从真实用户desktop读取Exec，原参数启动Snapshot并选择前摄，约35秒获得2042个递增PTS缓冲、2031次sink render调用、0回收错误/0paintable Bus Error，无GPU FD及新增GPU fault，退出完整恢复。render调用数不等于物理屏幕呈现帧数；没有在GUI触发快门，后端保存证据仍按下文分别解释。[实际GUI预览](gui-flow-validation.json)

用户强调应用无需逐个修改即可使用相机，后续以公共后端修复为目标。内核传感器/CSI/V4L2、libcamera处理与PipeWire/GStreamer各自有缓冲责任；目前没有证据把这个用户态引用错误归因于内核，不为移除应用开关而盲改内核。已有r1及启动覆盖是临时缓解，不能宣称其它客户端已经修复。

进一步隔离诊断保留共享pool，不设置复制环境：341次错误全部发生在GStreamer原缓冲仍有1个引用时，SPA缓冲均只有2项metadata、缺少Busy元数据。这里只证明交付/引用状态及元数据缺失，Busy缺失与提前复用的因果链仍待对照验证；不能直接宣称加Busy就能修好。诊断插件只在独立搜索目录加载，未替换已装r1。下一步核对SPA libcamera元数据协商、生产端回收和客户端队列，完成公共路径修复后去掉逐应用开关，并用不同标准客户端复测。[所有权收据](ownership-validation.json)

## 本轮结论

已稳定复现：消费者跨帧持有共享缓冲时，PipeWire/GStreamer报告尚未回收的缓冲再次交付。单纯降低消费速度未复现；不能把旧问题归为一般慢帧。复制帧可绕开该复现场景，底层提前复用的完整根因仍需进一步定位。

| 实机路径 | 时长 | 接收帧 | 未回收错误 | 结果 |
| --- | --- | --- | --- | --- |
| 发行1.6.9，快速消费 | 12秒 | 682 | 0 | PTS递增，退出释放 |
| 发行1.6.9，逐帧延迟40ms | 12秒 | 286 | 0 | PTS递增，退出释放 |
| 发行1.6.9，跨线程至少持有120ms | 12秒 | 345 | 339 | 稳定复现旧错误 |
| 上游锁修复候选，显式关闭共享pool，同样持有 | 12秒 | 690 | 0 | PTS递增，退出释放 |
| 完整特性候选，应用级复制开关，同样持有 | 12秒 | 687 | 0 | 开关生效，退出释放 |
| 原生APK安装后，从系统路径加载，同样持有 | 30秒 | 1728 | 0 | PTS跨度29.869秒，默认策略/重配置检查通过 |

依据：[共享复现](flow-1000000-validation.json)、[复制候选](flow-3000001-validation.json)、[已安装系统路径](flow-4000000-validation.json)。日志中新缓冲数可能比最终sink接收数多1～2，这是停流时尚未交付至sink的缓冲；不是屏幕实际呈现帧数。所有成功测试的格式、图、控制、供电、运行时PM和MCLK均恢复，无新增GPU fault/WARN/Oops，taint0。跨帧持有样本由主线程释放，模拟显示端异步保留帧；它不是GTK实屏验收。

## 实现、安装和回退

[配方](../../linux-port/packages/gst-plugin-pipewire/APKBUILD)采用上游1.6.9及两个小补丁：回移上游[30ff8da](https://github.com/PipeWire/pipewire/commit/30ff8da174121567c06a576bf2a83e71779ee991)，把可能触发最后一次unref的操作移到PipeWire循环锁之外；另在设备provider创建视频源时识别本地 `SAMURAI_CAMERA_COPY=1`，设置已有 `use-bufferpool=false` 属性。未设置开关的客户端保持上游默认；同一source的目标重配置继续保持复制策略。[来源锁](../../linux-port/packages/gst-plugin-pipewire/source-lock.json)

ARM64插件保留DMA-DRM、设备provider及SHM allocator构建选项。先以独立插件目录/registry测试，再将已核产物纳入原生签名APK。官方r0 APK使用既有Alpine公钥验签，本地r1使用手机既有项目公钥验签；没有增加信任密钥。原包唯一载荷文件被替换，依赖和install-if保留。[构建](profile-build-validation.json)、[签名APK](package-build-validation.json)、[实际安装](package-install-validation.json)

实际APK事务只改变一个包记录；原944及后续其它用户态包均未动。`apk add`本地文件自动在world增加该包的APK3校验和约束，这是本轮唯一world新增项。升级完整系统或制作rootfs时要纳入此约束/修复配方，不能仅复制libcamera r15。旧r0 APK、原插件、APK数据库及world前镜像保存在手机 `/var/lib/samurai/k262-package-inputs`、`k262-package-transaction-r2` 和PC私人262目录。原生降级模拟通过，未实际执行往返降级。

现有两项用户启动覆盖增加复制开关，同时保留Cairo及 `GDK_DISABLE=gl,vulkan,offload`。会话D-Bus ReloadConfig成功；不是全局环境变更，没有启动相机窗口、强制解锁或重启桌面。[启动配置事务](launcher-install-validation.json)、[配置副本](../../linux-port/camera/snapshot-launcher/org.gnome.Snapshot.service)。回退启动配置须先比对该事务中的after哈希，保留用户后续修改，再恢复对应before副本。插件回退按当前APK数据库重新模拟，只降级此包；无需刷boot。

## 拍照和画面

已实际走 `PipeWire/libcamera → wrappercamerabinsrc → camerabin → JPEG`，生成私人前摄样本。第二次取得 `start-capture`、`image-done`、831062字节文件及正常停流；复制候选再次取得 `image-done` 和730675字节文件，回收错误0。[正常保存收据](probe-2000001-validation.json)、[复制路径拍照](probe-3000002-validation.json)

首张873374字节JPEG可解码为1920×1080，私人导出SHA256一致。人工检查能辨识真实场景结构，整体偏暗且有明显噪点；128×72缩采样RGB均值约20.7/25.4/21.1。未控制照明、曝光或颜色参考，不能认定色彩、自动曝光或画质已完成适配。[解码与统计](front-photo-validation.json)。照片只保存在手机和PC私人目录，不纳入公开文档、源镜像或提交。

这次验证了真实后端快门/文件保存；没有点击Snapshot的桌面快门，未证明其图库更新、前后切换、录像和持续预览。IMX319暗帧、S5K3M5共享供电与19.2MHz驱动、GW1/其它后摄仍开放。240的S5K候选未被本轮编译部署。用户延期的纯色测试仍保持延期。

## 失败收据和续作

首次预检把 `apk info -v` 的输出误当作单行版本，取流前停止，随后改为原生版本存在查询。首次JPEG已保存，但原240派生harness在子进程恰好退出于两次poll之间时会漏掉管道输出；已补退出后的communicate收尾，并用第二次完整拍照收据验证。首张缺失的image-done消息没有追认。

首次APK模拟将Downloading误算作第二条变更，实际安装前停止；修正动作筛选后只真实安装一次。第一次安装后降级模拟使用了APK3不支持的 `--allow-downgrade`，仅模拟命令失败；另行只读核对当前插件/包库并使用显式旧APK成功模拟，没有重放安装。打包初次只选本地签名公钥集，官方包验签被拒；随后使用原SDK的Alpine＋项目既有公钥集，通过后才打包。原失败日志均保留。

下一步解锁后测Snapshot真实预览、快门保存和退出，重点检查原163/301次回收错误是否消失。随后追曝光/噪声及IMX319、S5K3M5。当前启动guard和严格运输见[检查点](../../NEXT-SESSION.md)；新代码在本目录，原始日志、签名APK、照片和完整证据仅 `E:/edk2-samurai-out/kernel262`。大多数实验上下文只能执行一次，重测应新建上下文，勿覆盖旧收据或重放已安装事务。

[最终健康](final-health-validation.json)确认49项框架载荷、插件与启动配置哈希、961包、原Phosh/PipeWire/WirePlumber进程身份、空闲PM、无残留trace和所有worker终态；新增GPU故障0/taint0。[私人证据归档](evidence-validation.json)共274个文件、约9.94MB压缩包，PC导出总SHA256及逐成员SHA256全部通过。公开派生收据明确标注无GUI；旧harness中误导性的“30秒”“GTK实际renderer”等标签已澄清，原始收据保留在私人证据内。

后续GUI/所有权实验结束后的[再次健康检查](final-health-after-gui-validation.json)同样通过；[补充归档](evidence-addendum-validation.json)新增或变更51个文件、约1.22MB，含GUI与共享模式诊断原始日志，逐成员校验通过；首份274文件归档保持。通用修复尚未完成，下一轮从本页最上方方向接续。
