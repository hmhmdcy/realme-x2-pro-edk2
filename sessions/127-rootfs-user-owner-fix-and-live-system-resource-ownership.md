# 阶段127：rootfs账户权限修正与实机系统资源属主

2026-10-12。阶段127已补齐完整rootfs账户/属主缺口：60个home条目改为10000/10000，85个系统配置和固件资源改为root；修正前实际降权创建失败，修正后及F2FS编码镜像反向导出均实际读写删除成功。936包/770模块、21,131条目全量内容与metadata零差异、双fsck/逐块稀疏重建/UUID-label及匹配126四件套通过；镜像未全量刷入userdata。85项系统属主修正在当前#126实机增量部署，文件bytes/mode/11来源保持、taint0、桌面进程保持。#126内嵌DT与3帧内部TPG真实DMA已验收，物理camera/GPU/显示长稳等15组边界继续开放，goal active。

## 语义错误与真实降权验证

126 rootfs内容/metadata与原模板逐项相等，并不保证模板语义正确。账户uid/gid10000，而60个home条目为旧builder1000；另外85项Wi-Fi配置及本机固件资源也残留1000。系统etc/usr和特权usr文件本来root-owned，没有全树误归属；此前将145总数笼统归为home已纠正。实机home原本10000，所以不改手机home，不覆盖用户文件。

新rootfs127用cp -a隔离复制126模板，保留设备节点、symlink/hardlinks及metadata。fork/chroot到副本、清supplementary groups、降为uid/gid10000，在.local执行O_EXCL创建、写入、seek/read核对、关闭和unlink：修正前真实EACCES，修正后成功。60项home10000/10000、85项系统资源0/0，内容/mode/xattr/其它ownership保持；chown后恢复原mode，避免丢setgid。源码126模板未改。一次60/145计数假设失败后已核对实际路径和范围，明确分别修正；没有放宽成忽略计数或任意全树chown。

## 新完整镜像

F2FS sparse 1817933412 bytes，展开119033245696 bytes，SHA256 `215a53431abaf4fe878416e9601a9190b8de9c9f4000af341fdf3ee33110fe09`，路径E:/edk2-samurai-out/kernel127/samurai-rootfs-f2fs-k127-device-fixed.simg。仍匹配kernel126独立release及770模块，936软件包。两次readonly fsck十项Ok、payload逐块比较、SKIP范围实际source hole核验、两个superblock私有UUID/pmos_root保持。

实际稀疏重建raw经readonly loop，用固定修正版dump工具导出21131条目，内容、类型、mode、UID/GID、链接、设备号与xattrs零差异。encoded passwd10000与home/.local10000一致，无残留UID1000，/dev/null为字符设备，生成根目录root0/0/0755。在**实际导出的编码镜像**再次fork/chroot降权，确认home可写/可遍历并实际创建读写删除成功。新增stage marker使条目比126多1。

四件套引用126嵌入DT boot d85f110275758c981691daf0d189a50c4ae45e718da4b947085ca624c6b653f8、126logdump5684fee4cf88d9edea0aed503606f3f81735e1a9fb6fce0c51aa766ebd38c8b2、126模块62bfd60937b992d0f59063d70bd7b40f4cfa73668d7b894641f289e734753510及本127rootfs，实际所有文件hash/size再核对。#126 boot/logdump/模块与三帧TPG已实机验证；127完整镜像尚未全量部署或冷启动。所有userdata/runtime资料增量保持，不擦除当前用户数据。

## 实机增量修正

只选择85个系统资源路径，逐一限定/etc/samurai-wifi与/usr/lib/firmware、无symlink、type/mode/整文件SHA与模板一致，再执行chown0/0和原mode恢复。初次preflight发现本机c28/c35试验文件属主为10000，守卫在任何系统属主修改前拒绝；保存诊断，第二次只允许这两个明确本机trial路径在hash精确相等时接受10000，其他路径仍只接受0/1000。两轮私有preflight目录均保留，没有覆盖失败证据。

全部85条目前后文件hash和mode精确保持，新owner全root。私有归档逐成员SHA通过，NV6/source4/vendor1共11hash通过，home仍10000/10000且未写，Phosh/Phoc运行、taint0。仅持久文件metadata变化，未改固件payload、GPIO/I2C/MMIO、电源、boot/logdump或NV/GPT。没有将无kernel改动的metadata修复伪装成另一个内核刷入；用户要求的静态补丁刷入/日志验证已在126完成，127以增量部署与实机回读验收。

## 清理与挂载收尾

126 software sparse与source保留诊断；127正确镜像验收后，对两份被替代的126 raw逐data/fill byte和SKIP source hole重新核验，确认可由保留的126 sparse恢复、无loop使用、路径/inode/mtime/size保持后才unlink。删除2文件，实际分配释放3894976512 bytes，E126内卷余9147305984 bytes。新127源码/raw/重建raw/export/sparse全部保留，115/118稳定boot/logdump/模块/源码未动。

此前126在C/WSL归档回读后删除110/112/114的15189个生成ignored ELF，实际2.49GiB，源码/配置/模块/Image和稳定版本保留。现在118/122/126三E私有卷串行sync/卸载，各自readonly e2fsck均0；未fsck/resize/compact原WSL VHD。宿主C余15979220992 bytes，E余42538819584 bytes，不把guest逻辑free当宿主容量。

## 继续目标

完整硬件系统仍未验收：内部TPG只证明CSID0/VFE0/CPAS/IOVA/DMA路径；外部PHY/物理sensor/PM8008输入与enable/HAL settle留档。旧GPU像素失败、DPU启动超时及最终CRTC inactive未解决；GNSS真实fix、充电ADC/休眠、指纹等仍开放。下一轮优先一项可自动实测缺失功能，例如5GHz Wi-Fi有界复测与修复，再准备静态检查通过即刷入的匹配候选。若长期停滞，先记日志证据再换项。用户无需人工检查，goal继续active。
