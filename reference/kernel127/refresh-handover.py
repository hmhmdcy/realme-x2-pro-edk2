from pathlib import Path
import json,re
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel127'
assert json.loads((ref/'complete-bundle-validation.json').read_text())['rootfs_home_ownership_matches_passwd']
image=json.loads((ref/'rootfs-image-validation.json').read_text());vol=json.loads((ref/'host-volume-validation.json').read_text())
(r/'NEXT-SESSION.md').write_text(f'''# Realme X2 Pro 继续检查点（阶段127，2026-10-12）

goal active。当前内核126与嵌入CAMSS设备树已实际刷入，内部CSID0→VFE0 TPG三帧真实DMA/IOVA/IRQ/内容/电源恢复通过。完整rootfs127修正60个home与85个系统资源属主，936包/770模块/21131条目反向内容和metadata零差异、双fsck/稀疏重建及encoded降权访问通过。85项系统metadata已增量上机，桌面/taint0/11来源保持；完整userdata镜像尚未全量刷入或冷启动。物理camera/GPU/显示长稳/GNSS fix/充电休眠/指纹等仍开放，不能标系统完整可用。

先读[阶段127](sessions/127-rootfs-user-owner-fix-and-live-system-resource-ownership.md)、[阶段126](sessions/126-tpg-dma-guards-full-rootfs-and-real-deployment.md)、[15组硬件](linux-port/docs/HARDWARE-STATUS.md)。用户要求自动飞轮、互联网/原厂源码/反编译线索、长难错留档换项、静态补丁通过即刷入并检查日志；清理经验证obsolete产物，保留稳定版本，不做需要人工观察的工作。

## 当前设备与匹配包

手机kernel #126，release 7.3.0-rc6-rmx1931-samurai-k126+。最新boot身份在E:/edk2-samurai-out/kernel126/embedded-boot-id-private.txt及phone /var/lib/samurai/k126-embedded-runtime/boot-id-private.txt，元数据127修正没有重启。旧source/current boot-id属于之前启动，不能拿来冻结当前boot。

boot d85f110275758c981691daf0d189a50c4ae45e718da4b947085ca624c6b653f8，logdump5684fee4cf88d9edea0aed503606f3f81735e1a9fb6fce0c51aa766ebd38c8b2，modules62bfd60937b992d0f59063d70bd7b40f4cfa73668d7b894641f289e734753510。正确完整rootfs127 {image['sha256']}，{image['sparse_bytes']} bytes；见reference/kernel127/complete-bundle-validation.json，各镜像/固件/密钥/手机dump只在E:/edk2-samurai-out私有目录。

126第一次只更新FAT DTB未生效，真实日志发现后已补建并刷入boot内嵌DT，live DT全节点/预期属性精确匹配。以后DT改动必须canonical UEFI audit、非DT可执行模块byte保持、原UEFI源码/FD/FV/boot恢复，再实际live DT核验；不能只改FAT认为设备树已部署。

手机当前Phosh/Phoc运行、Wi-Fi up、MPSS/ADSP/hci0有启动证据、taint0。最新boot累计DPU1/GPU0，50.19秒窗口0新增故障，最终CRTC inactive；旧118 GPU像素失败没有重跑或修复，不能因新boot0fault认定GPU正常。TPG仅内部数据路径，物理sensor供电仍关闭。

## 构建与清理

E私有卷118(20GiB)、122(24GiB)、126(24GiB)均已串行sync/卸载、readonly e2fsck0。127的rootfs127/raw/restored/export在E126卷/home/cy122/pmos-samurai-build126，读取前用reference/kernel126/ensure-build-volume.py，统一WSL -u root，mount/unmount由root-owned flock串行；不要在上一步返回session_id但未terminal时启动依赖。

E126内卷余{vol['volumes'][2]['inner_volume_free_bytes']} bytes。C/WSL已将obsolete110/112/114的15189个ignored生成ELF归档逐member回读后删除，实际2.49GiB；源码/.config/Module.symvers/Image/DTB/cpio/.ko及稳定109/111/113/115/118保持。两个被127替代的126 raw也经新鲜sparse payload/holes恢复证明后删除；126 sparse/源码保留诊断，新127源码/raw/export/sparse保持。宿主C余{vol['host_c_free_bytes']} bytes、E余{vol['host_e_free_bytes']} bytes，不resize/compact原VHD。

126/127 prepare/stage/quiesce/pack/owner/cleanup/flash脚本为已执行的一次性工具，不重放。127模板首个WSL请求曾超时但未启动副本，readonly fsck0；后来60/145计数假设失败已明查并修正为60 home/85 sys，源模板保持。文件复制用cp -a保留类型/设备/hardlinks/owner/mode，普通copyfile不适合dev节点。

## 下一项及部署纪律

优先推进一项可自动实测的缺失功能，例如5GHz Wi-Fi有界复测/修复，或initramfs初始console节点。物理camera/PM8008四输入/全芯片enable/HAL settle、GPU CCU fault、GNSS真实fix、充电ADC事件等长难项先留档，不重做已通过的离线证明代替硬件验收。新kernel/static补丁检查通过后实际刷入并比对日志，保留115/118与当前126恢复材料。

新刷入要取得最新boot身份/分区备份/GPT18/11来源，排空GUI/DRM/audio/radio，trace先保存再关闭，sync+fsfreeze成功回执后单次9002/F1，独立fastboot身份/大小守卫。失败先采当前状态，不盲重复OUT/reset。若未来全量部署rootfs127，先保存最新userdata/用户配置和旧模块以保持恢复能力，不直接erase。
''')
# Keep the 15 rows current without turning limited observation into acceptance.
p=r/'linux-port/docs/HARDWARE-STATUS.md';t=p.read_text()
rows={
'原生显示面板':'| 原生显示面板 | 新#126嵌入DT boot恢复DRM/card1/Phosh/Phoc，taint0；本boot累计DPU1，50.19秒窗口0新增，最终CRTC inactive | 持续绘制/命令帧/休眠与长稳；进程存活和inactive窗口不能认定显示修复 |',
'普通USB与OTG':'| 普通USB与OTG | 当前#126 NCM/SSH/SCP可达；两轮当前boot冻结/F1单OUT回执，logdump后纠正boot内嵌DT，native分区和live DT核验通过 | OTG/USB3/休眠/长稳，保留host usbmon及物理by-path守卫 |',
'Wi-Fi':'| Wi-Fi | 当前#126 wlan up，启动QMI/WCN3990正常；历史2.4GHz NetworkManager与HTTPS下载验收保留，127系统配置/固件owner为root且bytes保持 | 5GHz有界失败待修、当前完整网络请求回归、冷启动/休眠/长稳 |',
'蓝牙':'| 蓝牙 | #126匹配release的三模块运行，QCA UART firmware setup完成/hci0存在；legacy/current .text相同、rootfs动态模块路径修复 | 新扫描回归及UART retry错误/冷启动稳定性；不要求配对连接 |',
'音频':'| 音频 | #126 ADSP/card0运行，最终PCM closed双功放off/muted/failed0；历史UCM/扬声器/DMIC0电气验收保留 | 自动音频回归、实际音质/耳机/DSM/校准/休眠未验收 |',
'蜂窝网络/数据':'| 蜂窝网络/数据 | 当前#126原fixed IPA代码保持/匹配模块，MPSS运行/rmnet_ipa0，NV6/source4保持；历史MM sim-missing边界保留 | 移动数据/通话未验收，clock/ICC压力、SSR/冷启动/休眠/长稳 |'}
for name,row in rows.items():t,n=re.subn(r'^\| '+re.escape(name)+r' \|.*$',row,t,flags=re.M);assert n==1
p.write_text(t);print('K127_COHERENT_CURRENT_HANDOVER_15_GROUPS_REFRESHED')
