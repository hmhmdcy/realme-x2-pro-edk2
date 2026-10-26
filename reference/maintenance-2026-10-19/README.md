# 2026-10-19：暂停交接与编译产物清理

本轮按用户要求整理交接并释放主机空间。相机适配目标保持暂停，未启动手机实验、刷写、重启或安装候选。最后实机结论来自302，不能把本轮主机检查算成新一次硬件验收。

## 接手时先读

[当前检查点](../../NEXT-SESSION.md)、[操作边界](../../WORKING-BOUNDARIES.md)、[302实现与验收](../kernel302/README.md)。交接前九个入口的逐字原件及SHA256保存在[归档清单](../../archive/camera-before-handoff-2026-10-19/manifest.json)。302原检查点哈希按该归档阅读；本轮最终入口清单见checkpoint-validation.json。

实际手机仍是 **#298／7.3.0-rc6-rmx1931-samurai-k298+**；维护树`/home/cy122/x2pro-linux/camera279-isp-kernel`，分支samurai-blc298，提交`c5e118faec21a6c4bd2e7d5b86b3b21ad9dc2117`。产品libcamera0.7.2-r24／config-r19与PW／SPA／Gst1.6.9-r3仍走RAW＋CPU ISP。778模块、961包、50相机载荷全量核对沿用300最后记录。

302私人硬件pipeline／IPA候选未安装。IMX319当前模式的SensorHelper、DelayedControls、标准Manual曝光／增益及有效SOF元数据在最终隔离／签名线程测试合计960帧、36次控制变化通过。硬件AE／AWB、多摄／多模式、正式暗场、EEPROM完整布局和校验、完整IQ均未完成。原厂BLS参考与临时场景WB不能冒充本机暗场或工厂个体标定；用户选择先正常场景对照、暂不遮光。

302的R1—R4采集已终态，最后记录匹配worker／fixture／IPA均退出、图与控制恢复、资源自然休眠；不要重新播放旧launch或恢复脚本。再次操作手机时核对当前状态，不沿用旧启动身份盲目切换。

## 保留的恢复与续作材料

| 内容 | 保留位置与用途 |
| --- | --- |
| 当前#298镜像／logdump／778模块 | 私人`E:/edk2-samurai-out/kernel298`，本轮核对关键三包SHA256 |
| 稳定#290回退 | 私人kernel290的logdump及独立778模块包，本轮核对SHA256；kernel292/completed-boot290/vmlinux保留 |
| 当前完整内核构建输出 | `/mnt/samurai-full282/build`，E盘kernel282/full-kernel-build282.ext4，32 GiB原卷保留；用284/storage.py核验backing后挂载 |
| 当前SDK与产品基线 | `/home/cy122/x2pro-linux/libcamera214-root`；work/libcamera278-r24-r3-built及candidate278-r24保留完整输出 |
| 最新302源码与输出 | SDK/work/libcamera299-inline，名字虽含299，内容已是302；使用302/build-candidate.py，不能重放299／300源码安装器 |
| 最终302可运行包 | 私人kernel302/ipa-bundle-r2-private.tar.gz，SHA256 `a12020406954ba8663d92a53155445a8b04c532172392e428be9f109baa66c94` |
| 300已测源码及候选 | 私人kernel301/tested300-source-private.tar.gz、kernel300/ipa-bundle-r4-private.tar.gz保留 |
| 恢复资料和原厂依据 | k132776、248备份／return kit、原厂系统与调校BIN、EEPROM原始双读、固件／NV、场景样本、所有私钥均保留 |
| 传输身份与下一步细节 | 私人kernel298的SSH／身份资料，以及kernel302/next-actions-private.json保留；guard仍以实际状态核对 |

## 清理范围和重建影响

WSL删除约16.71 GB旧`.o`／`.a`中间文件：kernel109—136系列旧树、旧rootfs01内核、旧x2pro-linux/linux、camera269-full-build-r1、camera279-isp-build-r1，以及18个旧libcamera output目录中的对象／静态库。只删除明确的普通生成文件，检查无活动构建、无选中的Git跟踪预编译文件；源码、Git历史、配置、模块、Image、DTB、vmlinux、符号表和构建日志保留。当前279内核源码、302候选输出及产品r24-r3输出不在删除范围。

这些旧目录再次构建时需要重新编译对象；不能把“还剩部分输出文件”当作清理后已经重新构建通过。原配置／依赖文件仍在，由原构建入口重建缺失对象即可。当前302增量构建入口未受影响；内核构建保留Rust环境`/home/cy122/.cargo/bin`与`RUSTUP_HOME=/home/cy122/.rustup`。

E盘删除约11.93 GB：此前挪存的kernel282/host-pip-cache-preserved和kernel284/host-npm-cache-preserved下载缓存文件，以及16个旧completed-*中的中间vmlinux副本。保留所有对应配置、源码、镜像／模块和实验记录；#290调试vmlinux及当前构建卷不删。缓存今后按需重下载；已安装运行时不变。

kernel118旧20 GiB卷当前哈希与145归档不同，不能按重复副本删除。本轮先以只读方式确认目录，再另存完整压缩归档；仅在全量解压字节数与原卷SHA256一致、卸载并核对无loop占用后移除原卷。最终状态和空间数值以[清理收据](cleanup-validation.json)为准，旧145压缩归档也保留。

当前118卷的完整归档为私人`E:/edk2-samurai-out/cleanup20261019/kernel118-current-build-volume.ext4.zst`，解压后21474836480字节／SHA256 `f4a8328f0a5b2fe32c74695c70846ef4b7a176a98a23cf070c34a1ea4cc5bd96`。若需复现旧阶段，用zstd解压到新普通文件并核对该哈希，再挂载；当前内核构建用282卷，无需恢复118。原只读盘点的首次卸载因本轮du占用失败，停止该盘点后已正常卸载，无强制或懒卸载。

首次原卷删除检查因zstd仅保留秒级mtime而中止，未删除文件；修正为核对原卷完整时间戳及两文件整秒相同后继续。归档全量解压哈希检查始终保留。

私人数万条逐文件清单、大小／时间戳、删除完成标志及关键保留包前后哈希在`E:/edk2-samurai-out/cleanup20261019`。没有删除整个历史实验目录、原厂ROM、NV／校准备份或私人采集数据。

缓存文件清完后，递归删除两个空缓存目录的操作被自动审批拒绝，返回原因仅为策略阻止；未再次执行该操作，空目录保留。此拒绝不影响已完成的逐文件删除与主要空间回收。

WSL执行`sync`及根文件系统`fstrim`，未停止其代理／容器服务。TRIM报告的整个空闲地址范围不是新增释放量；WSL逻辑空间增量与C盘NTFS实测增量分别记账，不能相加。稀疏VHDX的逻辑长度不一定缩短；本轮不离线压缩、不重启WSL。

## 恢复适配后的顺序

1. 先验证曝光和模拟增益同时变化：20000µs×2与10000µs×4做恒EV对照，检查量化后的有效值、统计／图像帧关联和过渡帧；现有36次最终控制变化主要是一项一项改变。需要联合锁存时再根据原厂Sony group-hold描述和实测下沉传感器驱动。
2. 复用libipa AgcMeanLuminance、Histogram与ExposureModeHelper接硬件AE；自动控制回调携带epoch／revision，保存实际有效模式与延迟控制上下文，不能把发起request当作生效帧。仅在实现后开放Auto模式。
3. 补RGB统计与AWB、多摄／多模式、EEPROM布局／校验、正式暗场／颜色／阴影调校，以及取消、丢SOF、严重IRQ延迟、worker故障和队列回绕验证。Y BHIST不足以完成RGB AWB。

继续按SoC公共驱动、板级描述、传感器驱动、libcamera pipeline／IPA分层收敛。现有本地内核派生、配方补丁及ignore_unused尚未证明上游接受或跨版本零补丁升级；GPU默认故障、旧modem watchdog、SSC偶发EPERM仍未关闭，`whole_system_healthy=false`。

## 实测空间结果

| 文件系统 | 清理前可用 | 清理后可用 | 可用空间增加 |
| --- | ---: | ---: | ---: |
| C盘（GB，十进制） | 3.87 | 12.72 | 8.85 |
| E盘（GB，十进制） | 13.14 | 41.30 | 28.16 |

WSL根文件系统自身可用空间增加16.89 GB；此数与C盘回收重叠，不另加。旧118原卷21.47 GB压缩为5.25 GB，全量解压SHA256与当前原卷一致后删除原卷。数值为收尾时的实测，后台服务会使空闲空间小幅变化。
