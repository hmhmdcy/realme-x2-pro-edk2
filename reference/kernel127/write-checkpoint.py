from pathlib import Path
import json,re
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel127';get=lambda n:json.loads((ref/n).read_text())
image=get('rootfs-image-validation.json');bundle=get('complete-bundle-validation.json');fix=get('home-owner-fix-validation.json');live=get('live-system-owner-validation.json');cleanup=get('superseded-raw-cleanup-validation.json');vol=get('host-volume-validation.json')
assert image['both_fsck_pass'] and bundle['decoded_encoded_image_actual_unprivileged_create_read_write_unlink_pass'] and live['metadata_fix_live_deployed'] and vol['all3_private_e_volumes_unmounted_readonly_fsck_zero']
session='sessions/127-rootfs-user-owner-fix-and-live-system-resource-ownership.md'
summary='阶段127已补齐完整rootfs账户/属主缺口：60个home条目改为10000/10000，85个系统配置和固件资源改为root；修正前实际降权创建失败，修正后及F2FS编码镜像反向导出均实际读写删除成功。936包/770模块、21,131条目全量内容与metadata零差异、双fsck/逐块稀疏重建/UUID-label及匹配126四件套通过；镜像未全量刷入userdata。85项系统属主修正在当前#126实机增量部署，文件bytes/mode/11来源保持、taint0、桌面进程保持。#126内嵌DT与3帧内部TPG真实DMA已验收，物理camera/GPU/显示长稳等15组边界继续开放，goal active。'
doc=f'''# 阶段127：rootfs账户权限修正与实机系统资源属主

2026-10-12。{summary}

## 语义错误与真实降权验证

126 rootfs内容/metadata与原模板逐项相等，并不保证模板语义正确。账户uid/gid10000，而60个home条目为旧builder1000；另外85项Wi-Fi配置及本机固件资源也残留1000。系统etc/usr和特权usr文件本来root-owned，没有全树误归属；此前将145总数笼统归为home已纠正。实机home原本10000，所以不改手机home，不覆盖用户文件。

新rootfs127用cp -a隔离复制126模板，保留设备节点、symlink/hardlinks及metadata。fork/chroot到副本、清supplementary groups、降为uid/gid10000，在.local执行O_EXCL创建、写入、seek/read核对、关闭和unlink：修正前真实EACCES，修正后成功。60项home10000/10000、85项系统资源0/0，内容/mode/xattr/其它ownership保持；chown后恢复原mode，避免丢setgid。源码126模板未改。一次60/145计数假设失败后已核对实际路径和范围，明确分别修正；没有放宽成忽略计数或任意全树chown。

## 新完整镜像

F2FS sparse {image['sparse_bytes']} bytes，展开119033245696 bytes，SHA256 `{image['sha256']}`，路径E:/edk2-samurai-out/kernel127/samurai-rootfs-f2fs-k127-device-fixed.simg。仍匹配kernel126独立release及770模块，936软件包。两次readonly fsck十项Ok、payload逐块比较、SKIP范围实际source hole核验、两个superblock私有UUID/pmos_root保持。

实际稀疏重建raw经readonly loop，用固定修正版dump工具导出21131条目，内容、类型、mode、UID/GID、链接、设备号与xattrs零差异。encoded passwd10000与home/.local10000一致，无残留UID1000，/dev/null为字符设备，生成根目录root0/0/0755。在**实际导出的编码镜像**再次fork/chroot降权，确认home可写/可遍历并实际创建读写删除成功。新增stage marker使条目比126多1。

四件套引用126嵌入DT boot d85f110275758c981691daf0d189a50c4ae45e718da4b947085ca624c6b653f8、126logdump5684fee4cf88d9edea0aed503606f3f81735e1a9fb6fce0c51aa766ebd38c8b2、126模块62bfd60937b992d0f59063d70bd7b40f4cfa73668d7b894641f289e734753510及本127rootfs，实际所有文件hash/size再核对。#126 boot/logdump/模块与三帧TPG已实机验证；127完整镜像尚未全量部署或冷启动。所有userdata/runtime资料增量保持，不擦除当前用户数据。

## 实机增量修正

只选择85个系统资源路径，逐一限定/etc/samurai-wifi与/usr/lib/firmware、无symlink、type/mode/整文件SHA与模板一致，再执行chown0/0和原mode恢复。初次preflight发现本机c28/c35试验文件属主为10000，守卫在任何系统属主修改前拒绝；保存诊断，第二次只允许这两个明确本机trial路径在hash精确相等时接受10000，其他路径仍只接受0/1000。两轮私有preflight目录均保留，没有覆盖失败证据。

全部85条目前后文件hash和mode精确保持，新owner全root。私有归档逐成员SHA通过，NV6/source4/vendor1共11hash通过，home仍10000/10000且未写，Phosh/Phoc运行、taint0。仅持久文件metadata变化，未改固件payload、GPIO/I2C/MMIO、电源、boot/logdump或NV/GPT。没有将无kernel改动的metadata修复伪装成另一个内核刷入；用户要求的静态补丁刷入/日志验证已在126完成，127以增量部署与实机回读验收。

## 清理与挂载收尾

126 software sparse与source保留诊断；127正确镜像验收后，对两份被替代的126 raw逐data/fill byte和SKIP source hole重新核验，确认可由保留的126 sparse恢复、无loop使用、路径/inode/mtime/size保持后才unlink。删除2文件，实际分配释放{cleanup['allocated_bytes_removed']} bytes，E126内卷余{cleanup['inner_e126_free_after']} bytes。新127源码/raw/重建raw/export/sparse全部保留，115/118稳定boot/logdump/模块/源码未动。

此前126在C/WSL归档回读后删除110/112/114的15189个生成ignored ELF，实际2.49GiB，源码/配置/模块/Image和稳定版本保留。现在118/122/126三E私有卷串行sync/卸载，各自readonly e2fsck均0；未fsck/resize/compact原WSL VHD。宿主C余{vol['host_c_free_bytes']} bytes，E余{vol['host_e_free_bytes']} bytes，不把guest逻辑free当宿主容量。

## 继续目标

完整硬件系统仍未验收：内部TPG只证明CSID0/VFE0/CPAS/IOVA/DMA路径；外部PHY/物理sensor/PM8008输入与enable/HAL settle留档。旧GPU像素失败、DPU启动超时及最终CRTC inactive未解决；GNSS真实fix、充电ADC/休眠、指纹等仍开放。下一轮优先一项可自动实测缺失功能，例如5GHz Wi-Fi有界复测与修复，再准备静态检查通过即刷入的匹配候选。若长期停滞，先记日志证据再换项。用户无需人工检查，goal继续active。
'''
(r/session).write_text(doc)
for name in ['README.md','FLYWHEEL.md']:
 p=r/name;t=p.read_text().replace('[阶段126]',f'[阶段127]({session})，[阶段126]',1);t=t.replace('\n阶段126已实际刷入','\n'+summary+'\n\n阶段126已实际刷入',1);p.write_text(t)
p=r/'DOCS-INDEX.md';t=p.read_text().replace('\n',f'\n\n- [阶段127：rootfs用户权限修正和实机系统属主增量验收]({session})：正确的127完整镜像匹配126内核，21131条目与encoded降权访问通过，85项增量实机回读。\n',1);p.write_text(t)
p=r/'linux-port/docs/HARDWARE-STATUS.md';t=p.read_text().replace('阶段126）','阶段127）',1);a=t.index('\n\n')+2;b=t.index('\n\n',a);t=t[:a]+'15组硬件保持。 '+summary+t[b:];t+='\n阶段127：最新完整软件rootfs127匹配已运行126，home/sys-resource owner修正及21131条目/encoded降权访问通过。实机85项metadata增量验收，userdata未擦除；不把软件镜像验收等同物理camera/GPU/显示/休眠全系统可用。\n';p.write_text(t)
p=r/'NEXT-SESSION.md';t=p.read_text().replace('（阶段126，2026-10-12）','（阶段127，2026-10-12）',1);a=t.index('\n\n')+2;b=t.index('\n\n',a);t=t[:a]+summary+t[b:];t=t.replace('先读[阶段126]',f'先读[阶段127]({session})、[阶段126]',1)
t+='''
## 阶段127已完成更新（优先于上文阶段126过程待办）

最新完整rootfs127正确匹配kernel126：60个home10000/10000、85个系统资源root，源及实际encoded export降权读写通过；936包/770模块/21131条目零差异、双fsck/sparse payload+hole/UUID-label/四件套均通过，未bulk flash userdata。85项系统资源属主已在当前126boot增量部署，11hash/bytes/mode/桌面/taint0保持，不改手机home。126 rootfs仅保留诊断，两个obsolete126 raw已新鲜恢复证明后删除；新127raw/source/export/sparse保留。

118/122/126三E卷已串行卸载readonly fsck0，下一读取通过root ensure对应卷；127数据在E126卷/home/cy122/pmos-samurai-build126。不要重跑126/127一次性prepare/pack/ownership/cleanup/flash脚本或使用旧source/current boot-id。最新phone启动身份仍126/embedded-boot-id，系统metadata已127。

下一优先可自动实测功能，例如5GHz Wi-Fi；长难物理camera/PM8008/GPU已留档。新kernel/static补丁通过后实际刷入并查日志，保留115/118/当前126稳定恢复资料。rootfs127全量冷启动尚未验收，若未来做bulk部署须先保存最新userdata和可恢复的旧模块/用户配置，不能直接erase。goal active。
''';p.write_text(t)
print('CHECKPOINT127_FULL_ROOTFS_OWNER_FIX_LIVE_DEPLOYED_STABLE_ROLLBACK_PRESERVED_GOAL_ACTIVE')
