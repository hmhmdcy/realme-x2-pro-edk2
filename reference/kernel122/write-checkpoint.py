from pathlib import Path
import json
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel122';out=Path('/mnt/e/edk2-samurai-out/kernel122')
image=json.loads((ref/'rootfs-image-validation.json').read_text());bundle=json.loads((ref/'complete-bundle-validation.json').read_text());cleanup=json.loads((ref/'obsolete-artifact-cleanup-validation.json').read_text())
assert image['encoded_image_full_directory_export_and_content_metadata_check_pass'] and bundle['matching_boot_logdump_rootfs_modules_complete']
assert cleanup['obsolete_raw_files_deleted']==4 and cleanup['all_four_freshly_proven_reconstructible_before_delete']
session='sessions/122-complete-k121-rootfs-and-verified-build-cleanup.md'
summary='阶段122完成匹配#121的完整F2FS软件rootfs：936包/770模块、双fsck、稀疏逐块/空洞重建、21,134条目反向导出内容及权限/UID/GID/符号链接/xattr零差异；修复sload漏/dev/null和dump丢特殊权限位，启动/模块/rootfs四件产物核验完成，均未部署。按新增第6项清理4个已逐块证明可重建的旧WSL raw副本，释放7.26GiB实际占用，保留稀疏基线和回退；手机仍#118/DPU2/GPU1，完整硬件goal active。'
text=f'''# 阶段122：匹配#121完整rootfs与经验证的旧构建清理

2026-10-12。上一轮121完成PM8008无IRQ基础，本轮继续实际完整系统目标，运行中用户新增第6项：检查C盘/WSL、清理已验证过时的构建产物。该要求已纳入，不改变GPU/摄像头及其余15组验收范围。{summary}

## 完整软件镜像与启动产物

E盘新建24GiB私有ext4卷kernel122/rootfs-build-volume.ext4，label samurai-rfs122，mount /home/cy122/pmos-samurai-rootfs122；不扩大原WSL VHD。每次访问同进程ensure-rootfs-volume.py，源码121继续ensure118构建卷。复制115/rootfs基线1.8GiB到E，完整替换module tree为121匹配770模块，不把CAMSS新配置模块直接装入当前118。

复制后20,124个非模块用户态条目的文件内容、模式/UID/GID和符号链接与基线相同，936包、APK world/installed、本机固件和既有服务保持。770 ko与121已验archive逐字节相同，ELF64 AArch64、单一匹配vermagic、modules.dep每引用存在、System.map depmod -e无诊断、无symlink。IPA stripped SHA bdd85687f4889cfe78ca7dbcd8974618fc1a523d65b4d3678f6800a42ceb2ce0保持。

采用[内核F2FS工具流程](https://www.kernel.org/doc/html/v7.2-rc4/filesystems/f2fs.html)，mkfs -t0保持sparse holes，再sload -P导入；[AOSP img2simg -s](https://android.googlesource.com/platform/system/core/+/refs/tags/aml_med_341513600/libsparse/img2simg.cpp)使用hole读取模式。并非把119GB连续复制到C：原始/重建raw在E卷为sparse file。自有校验器逐RAW/FILL chunk比较，DONT_CARE只允许对应实际source hole，不用跳过块掩盖source data。

最终可用软件候选是 **E:/edk2-samurai-out/kernel122/samurai-rootfs-f2fs-k121-device-fixed.simg**，{image['sparse_bytes']}字节，展开{image['expanded_bytes']}字节，SHA **{image['sha256']}**。两个raw均fsck --dry-run十项Ok，重建一致；两份superblock的原私有root UUID和pmos_root label均正确，UUID不公开。反向从重建raw的**kernel只读loop**导出全部21,134条目，内容/模式/UID/GID/rdev/符号链接/xattrs零差异。生成根inode为0755、UID/GID0，额外核对；host staging顶层目录555不充当root inode运行权限要求。根/lib→usr/lib保持。

boot-partition-k121-uefi-reused.img 100663296字节，UEFI boot115逐字节复用e9863902b2e9cd0cb02257f87d868989d69f613c66fbca3b6a7158a86b9c336f。logdump-k121-camera-basis.img 67108864字节SHA6b734cc06090c6c33a6a795045c67f083f9ba1a2f500e4f37ff52ea8840611c2，FAT仅Image/samurai.dtb，Image121/DTB121实际mcopy读回一致、fsck.fat -n通过。配套770模块archive仍private121/modules-k121-private.tar.gz，7065464字节SHAa0d778b79be5f453fb65d0d906e6d23b45197415346be0a56f16920e21971484。

complete-bundle-validation.json列明四件产物/哈希，kernel121、rootfs生成阶段122，不虚构kernel122。未部署，不宣称118兼容这些新配置模块，未全量刷/erase userdata。121 CCI仍disabled，PMIC/sensor尚未启用，CAMSS数据通路还未接通；**完整软件rootfs不等于硬件功能全部可用**。

## 反向验收抓到的两个真实问题

初版samurai-rootfs-f2fs-k121.simg SHA27c1c206aedbfac988815bde9e6620234d2ce3e5fe986302e580dc8963ab5772，虽然双fsck/稀疏重建通过，目录导出比较有16差异：一处/dev/null字符设备缺失，15处SUID/SGID模式位差异，其他内容一致。该初版不作为部署产物，保留私有simg/失败manifest便于复现。

Ubuntu f2fs-tools1.16.0无整目录导出选项。尝试v1.17.0 tag时官方不存在，clone失败且无残留工作树，保留日志；检查refs后取[上游固定commit83fd39a184df96db5def895ddc55bf68e720ef76](https://kernel.googlesource.com/pub/scm/linux/kernel/git/jaegeuk/f2fs-tools/+/83fd39a184df96db5def895ddc55bf68e720ef76)。所有源码/对象/DESTDIR在E，host仅小型uuid-dev依赖。首次构建实际通过，但检查fsck/dump.f2fs路径失败，因为alias仅由install规则创建；改用私有DESTDIR install、局部LD_LIBRARY_PATH，不安装system binaries。

读上游sload/dir代码确实只建dir/regular/symlink，虽识别CHR/BLK却未创建；这解释初版/dev/null实际丢失。扩展私有Linux打包工具：dentry保存Linux new_encode_dev，创建CHR/BLK inode，无data blocks，把设备号写入F2FS addr[1]。与当前kernel fs/f2fs/inode.c的addr0 old_decode/addr1 new_decode规则交叉核对。dump对应支持CHR/BLK、正确解码mknod。另dump原先chmod后lchown会清掉setuid/setgid；改为lchown后恢复**实际inode编码的模式**，不是拿source权限去覆盖导出结果。这15差异属于导出工具问题，并未声称原image模式本身全部错。

本地GPL补丁f2fs-tools-device-nodes-and-dump-mode.patch SHA1c598cfc51500910a347613ec960182d4b66e4bb3e2899e95b96ff104129214d，原native binary保留，patched SHAa940d781d6d89519d4a3c10a2e989d4a5b9a2fc28be7b597b9792f2cbe69a002。首个include anchor写错导致安全断言，只回滚那个精确首编辑再完成，不重置未知改动。

实际512MiB F2FS fixture包含两CHR（含511:65535）、一个BLK259:1025、SUID/SGID文件和symlink：format→patched sload→原系统fsck→只读loop→patched dump，六条目内容/模式/UID/GID/rdev/xattrs全等。随后完整镜像重打包/全量反向比较也零差异。工具修改在主机离线环境，没有手机I2C/GPIO/相机供电事务。

## 按第6项检查并清理C/WSL

先保存WSL home构建占用及C/WSL/E文件系统清单，完整清单私有。只选115阶段四个旧raw：final/restored和delay-fixed/delay-fixed-restored。两份E盘保留simg分别重新SHA核对，先前双fsck报告存在；四raw每一个都重新逐chunk比较RAW/FILL内容并核对SKIP实际hole、尺寸及无loop使用，全部通过后才删除。删除前再核inode/device/mtime及绝对父路径，只unlink这四文件，不递归删除source/用户目录。

四文件实际allocated合计**7790116864字节（7.26GiB）**；逻辑476GB来自sparse file大小，不能报成释放476GB磁盘。原WSL guest可用空间增量吻合。fstrim /成功；没有resize/原VHD fsck/Windows强制压缩或权限设置修改。C可用空间立即检查仍9.12GiB，随后WSL闲置周期实际观察延迟回收，bundle时复测**{cleanup['c_free_later_recheck_bytes']/1024**3:.2f}GiB**，按真实测量记录，不把guest释放与host立即释放混为一谈。

保留115/rootfs用户态基线、两个稀疏镜像、115/116/118/121源码、当前118及115回退boot/logdump、原始Downloads/源固件/私有身份数据。旧115 raw路径已不存在，历史verifier描述过去证据；需要时在E从保留simg重建，勿重新向C展开119GB镜像。

122初版的raw/restored及重复失败export也属于可重建旧副本，只有在修正版完整验收后才进行专项清理；以superseded-e-copy-cleanup-validation.json为实际完成证据。初版simg和原工具binary/manifest仍保留。不要清掉正在使用的122 rootfs/修正export或任意未知文件夹。

## 运行状态与下一轮

最终SSH只读same boot guard：手机仍118/taint0/Phosh3492/Phoc3190原PID/DPU2/GPU1、PCM closed、双功放powered0 muted1、SLPI offline vdd/vddio0，NV6/source4/vendor1共11 checksum保持。本轮无手机rootfs/module/boot/logdump写入，无桌面重启/负载；GPU真实失败仍开放。

下一轮先推进本机CAMSS DT/C-PHY/DMA/ICC/QoS和有限PM8008实际地址/输入资料核实，sensor BIN/模式仍缺，不能猜寄存器或电源。软件整套#121已有可验产物，后续部署用当前boot完整GUI/fbcon/音频/无线排空+sync/fsfreeze+host usbmon前置+单次F1回执，userdata增量保留；不要运行旧erase userdata脚本或把候选模块混入118。rootfs122生成脚本是一次性工具，原始/修正版都已完成，不重跑覆盖报告。继续GPU根因、传感器/GNSS/充电/指纹/休眠等15组缺口，不要求人工画面/触摸/听音，不外发消息/呼叫、不push。完整系统goal active。
'''
(root/session).write_text(text)
for name in ['README.md','FLYWHEEL.md']:
    p=root/name;t=p.read_text();t=t.replace('[阶段121]',f'[阶段122]({session})，[阶段121]',1);t=t.replace('\n阶段121完成','\n'+summary+'\n\n阶段121完成',1);p.write_text(t)
p=root/'DOCS-INDEX.md';t=p.read_text();t=t.replace('\n',f'\n\n- [阶段122：完整#121 rootfs与过时构建清理]({session})：21,134项反向验收、设备节点修正、匹配产物、WSL安全清理；未部署。\n',1);p.write_text(t)
p=root/'linux-port/docs/HARDWARE-STATUS.md';t=p.read_text().replace('阶段121）','阶段122）',1)
t=t.replace('下一项先完成匹配#121软件rootfs/启动产物、推进CAMSS数据通路；','匹配#121完整软件rootfs及启动/模块产物已完成并通过21,134条目反向验收，未部署；下一项推进CAMSS数据通路；')
t+='\n阶段122：936包/770模块完整rootfs匹配候选121，device-fixed镜像4f39f409382d87c5524fbf610fa0d262b3e58629a0f7f1fbee6afc62af5f1933；双fsck和21,134条目反向验收通过，尚未上机。C/WSL经验证清理四raw实际7.26GiB，稀疏基线/源/回退保持。现运行118及15组功能边界不因软件打包通过而改变。\n';p.write_text(t)
p=root/'NEXT-SESSION.md';t=p.read_text().replace('阶段121（2026-10-12）','阶段122（2026-10-12）',1);t=t.replace('完整系统goal active。','完整系统goal active。 '+summary,1);t=t.replace('先读[阶段121]',f'先读[阶段122]({session})、[阶段121]',1)
t+='\n阶段122最新：完整匹配#121软件rootfs及UEFI boot/logdump/module bundle已生成、未部署，private kernel122/*device-fixed.simg SHA4f39f409382d87c5524fbf610fa0d262b3e58629a0f7f1fbee6afc62af5f1933，1,819,014,784字节，936包/770模块/21,134条目反向零差异。初版simg 27c1c...漏/dev/null不能部署；patched主机F2FS tools已有节点+mode修复与实际fixture/全量反向校验。122 rootfs/tools在E24GiB卷/home/cy122/pmos-samurai-rootfs122，每访问同进程ensure122；kernel源码121在E118卷仍ensure118。C新增目标已检查，旧115四raw验证后删除、7.26GiB实际回收，保留两个E115 sparse及115/rootfs/源/回退，勿再依赖已删除raw路径。当前手机118没有改任何分区/模块，boot guard仍private119，11来源校验和DPU2/GPU1不变。下一优先CAMSS数据通路、有限PMIC资料/安全读身份设计；不要因disabled基础构建通过声称摄像头可用，不做人工检查。\n';p.write_text(t)
print('CHECKPOINT122_COMPLETE_SOFTWARE_ROOTFS_AND_VERIFIED_CLEANUP_GOAL_ACTIVE')
