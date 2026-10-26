from pathlib import Path
import json,re
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel128'
load=lambda name:json.loads((ref/name).read_text())
bundle=load('complete-bundle-validation.json');vol=load('host-volume-validation.json');cleanup=load('superseded-raw-cleanup-validation.json');elf=load('obsolete-vmlinux-cleanup-validation.json')
assert bundle['decoded_encoded_image_actual_unprivileged_create_read_write_unlink_pass'] and vol['all3_private_e_volumes_unmounted_readonly_fsck_zero']
link='[阶段128](sessions/128-wcn3990-pairwise-key-delete-and-5ghz.md)'
status='阶段128已实际刷入#128，WCN3990/SNOC单播密钥删除的3.2秒超时实测降至0.018–0.027毫秒，四次安装确认保持；5GHz认证/DHCP/HTTPS/软件索引及NetworkManager服务重启自动连接通过。双频持久配置已增量上机，936包/770模块完整rootfs128已生成，21,132条目反向内容与metadata零差异、双fsck/稀疏重建/encoded UID10000实际读写及四件套通过；完整userdata镜像未全量部署。当前桌面/radio/hci0/5GHz/taint0，DPU累计1且最终CRTC inactive，旧GPU像素失败未修复，物理camera及其余硬件验收边界保留，goal active。'
for name in ['README.md','FLYWHEEL.md']:
 p=r/name;text=p.read_text();text=text.replace('[阶段127](',link+'，[阶段127](',1)
 first=text.index('阶段127已补齐');end=text.index('\n\n',first)
 text=text[:first]+status+text[end:];p.write_text(text)
p=r/'DOCS-INDEX.md';text=p.read_text();point=text.index('- [阶段127')
text=text[:point]+'- '+link+'：真实刷入128与单播key删除等待修复、5GHz自动连接、完整匹配rootfs128及安全清理。\n\n'+text[point:];text=text.replace('当前：[阶段119]','历史：[阶段119]',1);p.write_text(text)
p=r/'linux-port/docs/HARDWARE-STATUS.md';text=p.read_text().replace('阶段127）','阶段128）',1)
start=text.index('15组硬件保持。');end=text.index('\n\n',start);text=text[:start]+'15组硬件保持。 '+status+text[end:]
rows={
 '原生显示面板':('新#128复用126内嵌DT，DRM/card1/Phosh/Phoc及taint0；累计DPU1，50.15秒窗口0新增，最终CRTC inactive','持续绘制/命令帧/休眠与长稳；进程存活和inactive窗口不能认定显示修复'),
 '普通USB与OTG':('当前#128 NCM/SSH/SCP可达；本轮当前boot排空/冻结/F1单OUT回执，仅刷logdump，分区/live DT/GPT18核验通过','OTG/USB3/休眠/长稳，保留host usbmon及物理by-path守卫'),
 'Wi-Fi':('当前#128 WCN3990/SNOC单播删除0.018–0.027ms、安装确认保留；5180MHz认证/DHCP/网关/HTTPS和6034包索引，45.47秒及NM服务重启自主连接25.2秒通过；持久双频配置已部署','5GHz冷启动/休眠/长稳及历史非主动reason7掉线尚未验收；无外机固件或校准修改'),
 '蓝牙':('#128三匹配模块与QCA UART firmware setup/hci0存在；可执行段保持126，rootfs动态release路径保持','新扫描回归及UART retry错误/冷启动稳定性；不要求配对连接'),
 '音频':('#128 ADSP/card0运行，最终PCM closed、双amp idle/failed0；历史UCM/扬声器/DMIC0电气验收保留','自动音频回归、实际音质/耳机/DSM/校准/休眠未验收'),
 '蜂窝网络/数据':('当前#128 fixed IPA可执行代码保持126、770模块匹配，MPSS运行/rmnet_ipa0、11来源保持；历史MM sim-missing边界保留','移动数据/通话未验收，clock/ICC压力、SSR/冷启动/休眠/长稳'),
 '摄像头':('#126内部CSID0→VFE0 TPG3帧真实DMA/IOVA/IRQ/raw10内容/电源恢复通过；#128相同DT与模块可执行段保留，物理camera未验收','外部PHY/sensor/PM8008四输入与enable、HAL settle及物理stream、颜色次序/10bit范围/多模式和应用待办')}
for name,(done,todo) in rows.items():
 text,n=re.subn(r'^\| '+re.escape(name)+r' \|.*$',lambda m:f'| {name} | {done} | {todo} |',text,flags=re.M);assert n==1
text+='\n阶段128：'+status+' 初始console warning1留档，下一轮推进可自动验证的initramfs节点修复。\n';p.write_text(text)
session=r/'sessions/128-wcn3990-pairwise-key-delete-and-5ghz.md';text=session.read_text()
text=text.replace('新F2FS镜像已打包、双dry-run fsck及稀疏payload/holes重建通过；完整反向导出、实际降权访问与四件套收尾仍在进行。','新F2FS镜像双dry-run fsck、稀疏payload/holes重建、21,132条目反向内容/type/owner/mode/symlink/rdev/xattr零差异通过；编码镜像实际chroot降权UID10000创建/读写/删除通过，boot/logdump/rootfs/modules四件套逐SHA验证完成。镜像1,817,937,508字节，SHA256 326280a49951bafec4f9a3bd4ac400b9e84277c41364250e579bea34b7fb4fb8。')
text+=f'\n清理已完成：C/WSL obsolete110/112/114的3个vmlinux先用canonical objcopy分别证明与保留本地和导出Image相同，再将完整ELF私有归档逐member SHA回读后删除，实际分配{elf["allocated_bytes_removed"]}字节；稳定109/111/113/115/128 Image、源码diff/.config/Module.symvers/DTB/cpio保持，缺少证明的9个.o继续保留。E126卷两个被128替代的127 raw经新鲜稀疏payload/空洞恢复证明后删除，实际分配{cleanup["allocated_bytes_removed"]}字节；127 sparse/模板/export、128全部产物与115/118/126稳定回退保留。三个E私有卷串行sync/卸载/read-only e2fsck全部0；宿主C余{vol["host_c_free_bytes"]}、E余{vol["host_e_free_bytes"]}字节，不resize/compact原WSL VHD。\n'
session.write_text(text)
art={a['role']:a for a in bundle['artifacts']}
(r/'NEXT-SESSION.md').write_text(f'''# Realme X2 Pro 继续检查点（阶段128，2026-10-12）

{status}

先读{link}、[15组硬件](linux-port/docs/HARDWARE-STATUS.md)与reference/kernel128/complete-bundle-validation.json。用户要求自动飞轮、互联网/原厂源码/反编译线索、长难错留档换项、静态补丁通过即实际刷入日志验收；只清理经验证obsolete文件，稳定版本保留，无人工检查。

## 当前设备与产物

手机#128，release 7.3.0-rc6-rmx1931-samurai-k128+。当前启动身份只用E:/edk2-samurai-out/kernel128/embedded-boot-id-private.txt和phone /var/lib/samurai/k128-first-runtime/boot-id-private.txt；128 source-boot-id属于刷前126启动，不可拿来冻结当前boot。

boot {art['boot']['sha256']}（126内嵌DT，保持）；logdump {art['logdump']['sha256']}（本轮唯一实际刷分区）；modules {art['modules']['sha256']}；完整rootfs128 {art['rootfs']['sha256']}，{art['rootfs']['bytes']} bytes。所有镜像/配置/固件/身份/全日志只在E:/edk2-samurai-out私有目录。11来源/GPT18/实际分区SHA和770模块均已核验，旧118/126模块平行保留，userdata未擦除。

WCN3990/SNOC单播DISABLE_KEY只在WMI发送成功后跳过不存在的确认；SET/组密钥替换/其它芯片总线/nohwcrypt和发送错误保持。1152路径静态测试、实际126和128同条件trace对照通过。ath10k builtin，不能只换模块。原NM band=bg已移除，UUID/SSID/PSK/MAC/自动连接保持，NM正常服务重启自主5180连接；未验手机断电冷启动、休眠或长期稳定，历史reason7开放。

最终50.15秒6样本桌面/radio/hci0/5GHz/taint0，0新增DPU/GPU/内核故障；累计DPU1，最终CRTC inactive，旧118 GPU像素失败及CCU fault未修复。camera内部TPG126历史验收和相同128代码保持，不能写物理sensor可用。trace已保存关闭，camss DMA N/SLPI offline/传感器供电0/PCM closed/amp idle failed0。

## 构建、清理与卷

C/WSL /home/cy122/pmos-samurai-kernel128保留当前完整源码和构建；E126 /home/cy122/pmos-samurai-build126保留rootfs128/raw/restored/export及旧127模板/export。E118/122/126三个私有卷均sync卸载且read-only e2fsck0，下一次操作先在同一WSL -d Ubuntu -u root调用reference/kernel126/ensure-build-volume.py；统一root-owned flock，不在依赖前序session未terminal时启动下一项。

旧110/112/114 generated objects之前15,189项2.49GiB已恢复归档清理，本轮额外3个vmlinux回读归档、canonical Image等价后清理{elf['allocated_bytes_removed']}字节，源码与稳定构建保持，9个无cmd证明的.o保留。两旧127 raw清理{cleanup['allocated_bytes_removed']}字节，127完整sparse/模板/export仍可恢复。E126卷余{next(x['inner_volume_free_bytes'] for x in vol['volumes'] if x['volume']=='build126')}字节，C宿主余{vol['host_c_free_bytes']}、E余{vol['host_e_free_bytes']}字节。未resize/compact原VHD。

128 prepare/stage/trace/profile/cleanup/quiesce/flash为已执行的一次性脚本，不重放；已经没有运行的作业。初次trace filter EINVAL、早期GUI未就绪、SCP旧known_hosts引用失败已留档并纠正，不能覆盖初始失败证据。

## 下一项

优先有界处理initramfs初始console warning1：先取得128真实warning与实际cpio/init路径、匹配官方源码，不用删warning代替节点修复；若改动通过静态检查，构建新release/完整模块/rootfs并实际刷入验日志，保留128与115/118/126回退。物理camera/PM8008/HAL、GPU CCU、GNSS fix、充电休眠和指纹等长难项保留15组待办，按用户要求换项推进。

新刷入先取得当前boot身份/GPT18/11来源与实际partition备份，排空GUI/DRM/audio/radio，trace保存关闭，sync+fsfreeze成功后单次9002/F1；独立fastboot身份/分区大小守卫。失败采当前状态，不盲重复OUT/reset。完整rootfs128已可bulk部署但尚未部署，若未来全量写userdata先保存最新用户数据/配置与旧模块恢复材料，不直接erase。goal保持active，不能标系统完整可用。
''')
print('K128_CURRENT_CHECKPOINT_AND_ALL15_HARDWARE_DOCS_UPDATED',flush=True)
