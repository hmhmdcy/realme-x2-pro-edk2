from pathlib import Path
import json,re
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel129'
load=lambda name:json.loads((ref/name).read_text())
bundle=load('complete-bundle-validation.json');vol=load('host-volume-validation.json');cleanup=load('superseded-raw-cleanup-validation.json')
assert bundle['decoded_encoded_image_actual_unprivileged_create_read_write_unlink_pass'] and vol['all4_private_e_volumes_unmounted_readonly_fsck_zero']
link='[阶段129](sessions/129-initial-console-node-and-real-boot-verification.md)'
status='阶段129已实际刷入#129，initramfs增加root:root/0600字符5:1的console节点，实际启动warning由1变0。保留128单播密钥删除等待修复，新启动自主连接5180MHz，网关/HTTPS/6034包索引与50.44秒窗口通过；936包/770匹配模块完整rootfs129、21,133条目反向内容与metadata零差异、双fsck/稀疏重建/encoded UID10000实际读写和四件套验收完成。完整userdata镜像未全量部署。最终Phosh/Phoc/radio/hci0/5GHz/taint0，DPU累计3、CRTC inactive，物理camera、GPU像素及持续显示仍未通过，goal active。'
for name in ['README.md','FLYWHEEL.md']:
 p=r/name;text=p.read_text();text=text.replace('[阶段128](',link+'，[阶段128](',1)
 first=text.index('阶段128已实际刷入#128');end=text.index('\n\n',first)
 text=text[:first]+status+text[end:];text=text.replace('最新匹配镜像见阶段128','最新匹配镜像见阶段129',1);p.write_text(text)
p=r/'DOCS-INDEX.md';text=p.read_text();point=text.index('- [阶段128')
text=text[:point]+'- '+link+'：初始console实际启动修复、新启动5GHz自主连接、完整匹配rootfs129及安全清理。\n\n'+text[point:];p.write_text(text)
p=r/'linux-port/docs/HARDWARE-STATUS.md';text=p.read_text().replace('阶段128）','阶段129）',1)
first=text.index('15组硬件保持。');end=text.index('\n\n',first);text=text[:first]+'15组硬件保持。 '+status+text[end:]
text=text.replace('[阶段119](', '[阶段129](../../sessions/129-initial-console-node-and-real-boot-verification.md)、[阶段119](',1)
rows={
 '原生显示面板':('新#129复用126内嵌DT，DRM/card1/Phosh/Phoc及taint0；累计DPU3，50.17秒窗口0新增，最终CRTC inactive','持续绘制/命令帧/休眠与长稳；进程存活和inactive窗口不能认定显示修复'),
 '普通USB与OTG':('当前#129 NCM/SSH/SCP可达；仅刷logdump，分区/live DT/GPT18核验通过；9002单OUT完成、F1文本回执缺失，经独立只读fastboot验证后刷机','OTG/USB3/休眠/长稳，保留host usbmon及物理by-path守卫'),
 'Wi-Fi':('128单播删除0.018–0.027ms修复保持；#129新启动自主5180MHz认证/DHCP/网关3/3/HTTPS/6034包索引，50.44秒6样本通过；同一持久双频profile字节保持','5GHz物理冷启动/休眠/长稳及历史非主动reason7掉线尚未验收；无外机固件或校准修改'),
 '蓝牙':('#129三匹配模块与QCA UART firmware setup/hci0存在；可执行段保持128/126，rootfs动态release路径保持','下一项有界自动扫描/停止回归，UART retry错误/冷启动稳定性；不要求人工配对'),
 '音频':('#129 ADSP/card0运行，最终PCM closed、双amp idle/failed0；历史UCM/扬声器/DMIC0电气验收保留','自动音频回归、实际音质/耳机/DSM/校准/休眠未验收'),
 '蜂窝网络/数据':('当前#129 fixed IPA可执行代码保持128/126、770模块匹配，MPSS运行/rmnet_ipa0、11来源保持；历史MM sim-missing边界保留','移动数据/通话未验收，clock/ICC压力、SSR/冷启动/休眠/长稳'),
 '摄像头':('#126内部CSID0→VFE0 TPG3帧真实DMA/IOVA/IRQ/raw10内容/电源恢复通过；#129相同DT与模块可执行段保留，物理camera未验收','外部PHY/sensor/PM8008四输入与enable、HAL settle及物理stream、颜色次序/10bit范围/多模式和应用待办')}
for name,(done,todo) in rows.items():
 text,n=re.subn(r'^\| '+re.escape(name)+r' \|.*$',lambda m:f'| {name} | {done} | {todo} |',text,flags=re.M);assert n==1
text+='\n阶段129：'+status+' 下一轮推进蓝牙自动扫描/停止回归。\n';p.write_text(text)
p=r/'sessions/129-initial-console-node-and-real-boot-verification.md';text=p.read_text()
text=text.replace('四件套和encoded降权访问、清理与卷关闭收尾继续核对；完整userdata未全量刷入或擦除。','boot/logdump/rootfs/modules四件套逐SHA及encoded镜像chroot降权UID10000实际创建/读写/删除通过；完整userdata未全量刷入或擦除。')
text+=f'\n清理收尾通过：仅删除E126卷两个旧128 raw/restored，先新鲜逐payload/空洞证明可由保留128 sparse恢复，实际分配释放{cleanup["allocated_bytes_removed"]}字节（约3.63GiB）。旧128模板/sparse/export、当前129全部产物与稳定115/118/126回退保持；C/WSL本轮没有新增删除，9个无证明旧.o保留。E118/122/126/129四私有卷串行sync/卸载/read-only e2fsck全部0，宿主C余{vol["host_c_free_bytes"]}、E余{vol["host_e_free_bytes"]}字节，原WSL VHD未resize/compact。所有本轮作业已terminal。\n';p.write_text(text)
art={a['role']:a for a in bundle['artifacts']}
(r/'NEXT-SESSION.md').write_text(f'''# Realme X2 Pro 继续检查点（阶段129，2026-10-12）

{status}

先读{link}、[15组硬件](linux-port/docs/HARDWARE-STATUS.md)与reference/kernel129/complete-bundle-validation.json。用户要求自动飞轮、互联网/本机原厂源码/反编译线索、长难错留档换项，静态补丁通过后实际刷入日志验收；仅清理经验证obsolete文件、保留稳定版本，无人工检查。

## 当前设备与产物

手机#129，release 7.3.0-rc6-rmx1931-samurai-k129+。当前启动身份只用E:/edk2-samurai-out/kernel129/embedded-boot-id-private.txt与phone /var/lib/samurai/k129-first-runtime/boot-id-private.txt；129 source-boot-id属于刷前128启动，不可拿它冻结当前boot。

boot {art['boot']['sha256']}（126内嵌DT，保持）；logdump {art['logdump']['sha256']}（本轮唯一实际刷分区）；modules {art['modules']['sha256']}；完整rootfs129 {art['rootfs']['sha256']}，{art['rootfs']['bytes']} bytes。产物全部在E:/edk2-samurai-out/kernel129，具体文件名见complete-bundle-validation.json。所有配置/固件/身份/原始日志仅在E私有目录；11来源/GPT18/实际分区SHA/770模块已核验，旧118/126/128模块平行保留，userdata未擦除或全量刷入。

129仅在initramfs补dev/console字符5:1/root0600及匹配release/三BT模块；396成员其它内容与128保持，770模块可执行段与128/126相同，DTB逐字节相同。实际初始console warning0、用户态/init运行、Phosh/Phoc运行、taint0。128 WCN3990/SNOC单播DISABLE_KEY跳过不存在的确认修复保持，安装确认及其它芯片/总线/发送错误保持；ath10k builtin不可只换模块。

新启动自主5180连接、网关3/3、HTTPS200、Alpine索引6034包与50.44秒6样本通过，原双频profile字节/UUID/SSID/PSK/MAC保持；没有手动activation。未验物理断电冷启动、休眠/长稳，历史reason7仍开放。最终50.17秒6样本桌面/radio/ADSP/hci0/5GHz/taint0，0新增DPU/GPU/内核故障；累计DPU3，最终CRTC inactive，旧118真实GPU像素25失败未修复。内部TPG126历史验收代码保持，不能称物理camera可用。trace已保存关闭，camss DMA N/SLPI offline/sensor power0/PCM closed/amp idle failed0。

## 构建、清理与卷

C/WSL /home/cy122/pmos-samurai-kernel129与128源码/完整构建保留；新16GiB E129 volume mount /home/cy122/pmos-samurai-rootfs129，stage/rootfs129、image-export129-fixed、raw/restored全部保持。E126 /home/cy122/pmos-samurai-build126旧128 template/export/sparse保持，两旧128 raw经新鲜重建证明已清理{cleanup['allocated_bytes_removed']}字节。C本轮新增删除0，旧已归档objects/vmlinux清理保持，9个无证明.o仍保留，稳定109/111/113/115/128/129 Image存在。

E118/122/126/129四私有卷均sync卸载/read-only e2fsck0。操作E129必须在同一WSL -d Ubuntu -u root调用reference/kernel129/ensure-rootfs-volume.py；操作E126先调用reference/kernel126/ensure-build-volume.py。统一root-owned flock；所有前序依赖必须等session terminal，不因超时重启或重叠任务。宿主C余{vol['host_c_free_bytes']}、E余{vol['host_e_free_bytes']}字节，新完整构建先做空间守卫并优先现有E构建卷；不resize/compact原VHD。

129 prepare/stage/quiesce/entry/flash/cleanup/close等为已执行的一次性脚本，不重放。所有本轮作业terminal，当前设备未在测试任务中。

## 飞轮证据与下一项

第一次入口console-node-first没有9505，未发送OUT，自动解冻+根实际写探针通过；先经9501 eudtool com-up恢复9505 Shared，再做fresh Windows枚举并归一CRLF，然后冻结。第二次console-node-r2只发一次9002，完成2 bytes，F1文本回执缺失且没有重发。独立readonly fastboot serial/product/boot96MiB/logdump64MiB及fresh≤300秒证据通过，写前再验才刷logdump。保留缺口，不伪造F1回执；Windows JSON UTC已为DateTime Kind=Utc时用ToUniversalTime，不能再Parse丢Kind导致减8h。首次stale误判写前阻止，原观察已保留，第二观察重新验证。

下一项优先有界蓝牙自动扫描/停止回归，不配对、不要求人工观察；从当前129 boot fresh读取控制器、bluez/内核状态和错误计数，结束恢复原状态。长错先留档换项。GPU/持续显示、物理camera/PM8008/HAL、GNSS真实fix、充电休眠/指纹及其它15组边界保持，目标尚不能标完整可用。
''')
print('K129_DOCS_CHECKPOINT_UPDATED',flush=True)
