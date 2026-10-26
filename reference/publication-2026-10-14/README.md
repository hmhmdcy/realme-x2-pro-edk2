# 2026-10-14 分类提交与公开资料

用途：记录用户授权的代码分类、提交推送及隐私处理范围。当前硬件验收见[检查点](../../NEXT-SESSION.md)，本次没有重新构建、刷写或执行新的实机测试。

## 内核提交

Linux构建树保留99个源码/绑定文件的13个分类提交：共用trace事件、EUD、无线/remoteproc/QRTR、输入/触摸/振动、充电观测、传感器、ASoC/SLIMbus、IPA、CAMSS/PM8008、原生显示、A640 GPU、TLMM复位、设备树。先补入早期EUD console提交，再接入hmhmdcy/linux的samurai-bringup上游历史。

99个改动文件逐一SHA256相同；全部受跟踪源码与构建树匹配，上游额外保留tarball未导出的Documentation/.renames.txt元数据。提交前仅清理eud_earlycon.c两处空白行尾空格；原文保存在本地输出目录。15个显示相关文件仍与163编译收据一致，165保存的增量补丁逆向apply检查通过。五份.bak备份留在本地。

## EDK2与Mesa

164修复的BDS C/INF单独提交，[补丁](../kernel164/before-exit-panel-reset.patch)与现有源码一致。当前工作树DTB与boot164已验收内嵌DTB不同，本轮保留其本地改动，未将它纳入固件修复提交。

[Mesa0015](../../linux-port/patches/0015-mesa-turnip-a640-vm-bind-iova-alignment.patch)纳入EDK2仓库的保存补丁目录，并与146—151 GPU研究/验收证据一起提交。软件包/rootfs纳入补丁仍是后续工作。

## 公开副本与本地原文

公开资料保留代码、方法、成功/失败、计数及验收范围，设备标识、启动ID和真实无线地址替换为PRIVATE标记，数值身份字段为null或占位值；这些不是新的实测值。历史脚本的PRIVATE输入需要本地补齐，原始设备守卫仍应重新核对。

原始日志、密钥、私人身份、备份、Python缓存与原始二进制属性不提交。本地维护前快照保持逐字原文及原SHA256；公开快照脱敏，manifest同时记录private_original_sha256和公开文件SHA256。

同步和健康检查使用[公开副本生成工具](../../linux-port/scripts/public-docs.py)及[统一清单](../../linux-port/scripts/docs-sync-manifest.json)。本轮将早期标识脱敏、连接/音频、传感器/IPA/camera、rootfs/充电/故障调查、GPU、显示交接、文档工具及入口维护分别整理成提交。

## 分类提交清单

[提交与核对结果](commits-validation.json)记录Linux的14个提交与EDK2的10个分类/资产保留提交；携带本记录的后续文档提交不包含在该列表内。推送后按远端分支端点核对最终HEAD。
